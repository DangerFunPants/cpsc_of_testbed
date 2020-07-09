import nw_control.trial_provider    as trial

from trial_parameters   import TrialParameters, EbTrialParameters

import pickle       as pickle
import pprint       as pp

import numpy        as np

from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths
from collections                                        import defaultdict

class TuitiTrial:
    TX_RATE_SCALING_FACTOR = 10000

    @staticmethod
    def prune_flow_allocations_list(flow_allocations, flow_admissions):
        traffic_for_path_in_timeslot = {}
        for path_id in range(len(flow_allocations)):
            traffic_for_path_in_timeslot[path_id] = defaultdict(float)
            for request_id in range(len(flow_allocations[path_id])):
                for timeslot in range(len(flow_allocations[path_id][request_id])):
                    traffic_for_path_in_timeslot[path_id][timeslot] += \
                            TuitiTrial.TX_RATE_SCALING_FACTOR * flow_allocations[path_id][request_id][timeslot]

        return {path_id: [rate for rate in timeslot_to_rate.values()] 
                for path_id, timeslot_to_rate in traffic_for_path_in_timeslot.items()}

    @staticmethod
    def prune_path_capacity_list(path_capacities):
        capacity_for_path_in_timeslot = {}
        for path_id in range(len(path_capacities)):
            capacity_for_path_in_timeslot[path_id] = [tx_rate * TuitiTrial.TX_RATE_SCALING_FACTOR for tx_rate in path_capacities[path_id]]
        return capacity_for_path_in_timeslot

    @staticmethod
    def from_solver_file(path_like, id_to_dpid, network_topology):
        with open(path_like, "rb") as fd:
            trial_parameters = pickle.load(fd)

        # flow_allocations :: path_id -> timeslot_number -> volume of data per timeslot duration
        flow_allocations = TuitiTrial.prune_flow_allocations_list(trial_parameters.flow_allocations, 
                trial_parameters.flow_admissions)
        # path_capacities :: path_id -> time (in seconds) -> volume of data per second
        path_capacities = TuitiTrial.prune_path_capacity_list(trial_parameters.path_capacities)

        source_node, destination_node = (0, 1)
        disjoint_paths = list(node_disjoint_paths(network_topology, source_node, destination_node))
        if len(disjoint_paths) < trial_parameters.number_of_paths:
            raise ValueError((f"Not enough paths in the network to conduct trial {trial_parameters.trial_type}. "
                              f"Trial requests {trial_parameters.number_of_paths} but the network "
                              f"only has {len(disjoint_paths)} paths"))

        the_trial = trial.Trial(f"{trial_parameters.trial_type}")
        the_trial.add_parameter("duration", trial_parameters.trial_duration)
        the_trial.add_parameter("seed-number", "1234")
        the_trial.add_parameter("timeslot-duration", trial_parameters.duration_of_timeslot_in_seconds)
        the_trial.add_parameter("number-of-timeslots", trial_parameters.number_of_timeslots)
        the_trial.add_parameter("maximum-bandwidth-variation", 
                trial_parameters.maximum_bandwidth_variation)
        the_trial.add_parameter("flow-arrival-rate", trial_parameters.flow_arrival_rate)
        the_trial.add_parameter("mean-flow-duration", trial_parameters.mean_flow_duration)
        the_trial.add_parameter("mean-flow-demand", trial_parameters.mean_flow_demand)
        the_trial.add_parameter("number-of-admitted-flows", trial_parameters.number_of_admitted_flows)
        the_trial.add_parameter("number-of-successful-flows", trial_parameters.number_of_successful_flows)
        the_trial.add_parameter("number-of-paths", trial_parameters.number_of_paths)
        the_trial.add_parameter("flow-bandwidth-requirements", 
                {flow_id: trial_parameters.flow_bandwidth_requirements[flow_id]
                    for flow_id in range(len(trial_parameters.flow_bandwidth_requirements))})
        the_trial.add_parameter("deviation-mode", trial_parameters.deviation_mode)
        the_trial.add_parameter("profit", trial_parameters.profit)

        if isinstance(trial_parameters, EbTrialParameters):
            the_trial.add_parameter("confidence-interval", trial_parameters.confidence_interval)

        total_path_volume_per_second = (50 / 8) * 2**20
        total_path_volume = total_path_volume_per_second * trial_parameters.number_of_timeslots * \
                trial_parameters.duration_of_timeslot_in_seconds
        total_volume = total_path_volume_per_second * trial_parameters.number_of_timeslots * \
                trial_parameters.duration_of_timeslot_in_seconds * trial_parameters.number_of_paths
        total_bulk_transfer_volume = sum((sum(tx_rate_list) for tx_rate_list in flow_allocations.values()))
        total_remaining_capacity = sum((sum(tx_rate_list) for tx_rate_list in path_capacities.values()))

        scaling_factors = {}
        for path_id in flow_allocations.keys():
            max_remaining_capacity = max(path_capacities[path_id])
            trial_duration = trial_parameters.duration_of_timeslot_in_seconds * \
                    trial_parameters.number_of_timeslots
            total_remaining_capacity = max_remaining_capacity * trial_duration
            scaling_factor = (0.85 * total_path_volume) / total_remaining_capacity
            # scaling_factors[path_id] = scaling_factor
            scaling_factors[path_id] = 1.0

        # The flow transmission rates are traffic volume per timeslot duration.
        flow_set = trial.FlowSet()
        for path_id, tx_rate_list in flow_allocations.items():
            # Each rate should be in bytes per second now I think
            # scaled_tx_rate_list = [(tx_rate * scaling_factors[path_id]) / \
            #         trial_parameters.duration_of_timeslot_in_seconds for tx_rate in tx_rate_list]
            scaled_tx_rate_list = []
            for tx_rate in tx_rate_list:
                entries_for_this_rate = [(tx_rate * scaling_factors[path_id]) / trial_parameters.duration_of_timeslot_in_seconds] * \
                        trial_parameters.duration_of_timeslot_in_seconds
                scaled_tx_rate_list.extend(entries_for_this_rate)

            the_flow = trial.Flow(source_node, destination_node, scaled_tx_rate_list, disjoint_paths,
                    [0]*trial_parameters.number_of_paths)
            flow_set.add_flow(the_flow)
        the_trial.add_parameter("flow-set", flow_set)

        # The background traffic transmission rates are remaining path capacity per second
        background_traffic_flow_set = trial.FlowSet()
        # print(f"TOTAL PATH VOLUME PER SECOND: {total_path_volume_per_second}")
        remaining_capacities = []
        for path_id, tx_rate_list in path_capacities.items():
            scaled_tx_rate_list = []
            max_capacity = max(tx_rate_list)
            min_capacity = min(tx_rate_list)
            # if (max_capacity * scaling_factors[path_id]) > total_path_volume_per_second:
            #     print(f"Bad scaling on path with id {path_id} with max capacity of {max_capacity}")

            # print(f"Old tx rate list min: {min(tx_rate_list)}, max: {max(tx_rate_list)}")
            scaled_remaining_capacities = []
            for tx_rate in tx_rate_list:
                scaled_capacity = (tx_rate * scaling_factors[path_id]) / \
                        trial_parameters.duration_of_timeslot_in_seconds
                scaled_tx_rate_list.extend(
                        [total_path_volume_per_second - scaled_capacity] * \
                                trial_parameters.duration_of_timeslot_in_seconds)
                scaled_remaining_capacities.extend([scaled_capacity] * \
                        trial_parameters.duration_of_timeslot_in_seconds)
            remaining_capacities.append(scaled_remaining_capacities)
            
            # scaled_tx_rate_list = [total_path_volume_per_second - (tx_rate * scaling_factors[path_id])
            #         for tx_rate in tx_rate_list]
            the_flow = trial.Flow(source_node, destination_node, scaled_tx_rate_list, disjoint_paths, 
                    [0]*trial_parameters.number_of_paths)
            background_traffic_flow_set.add_flow(the_flow)
        the_trial.add_parameter("background-traffic-flow-set", background_traffic_flow_set)
        the_trial.add_parameter("transfer-volume-scaling-factor", scaling_factor)
        the_trial.add_parameter("expected-path-bandwidth-in-bytes-per-second", total_path_volume_per_second)
        the_trial.add_parameter("remaining-capacities", remaining_capacities)
        # the_trial.add_parameter("mean-background-traffic-tx-rate", mean_background_traffic_tx_rate)
        # the_trial.add_parameter("mean-bulk-transfer-tx-rate", mean_bulk_transfer_tx_rate)


        return the_trial

    @staticmethod
    def batch_from_directory(path_like, id_to_dpid, network_topology):
        trials = []
        for trial_file in (f for f in path_like.iterdir() if f.is_file() and f.suffix == ".p"):
            trials.append(TuitiTrial.from_solver_file(trial_file, id_to_dpid, network_topology))
        return trials

