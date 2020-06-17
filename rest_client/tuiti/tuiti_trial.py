import nw_control.trial_provider    as trial

from trial_parameters   import TrialParameters, EbTrialParameters

import pickle       as pickle
import pprint       as pp

from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths
from collections                                        import defaultdict

class TuitiTrial:
    @staticmethod
    def prune_flow_allocations_list(flow_allocations, flow_admissions):
        # aggregated_flow_allocations :: path_id -> list of tx rates indexed by timeslot
        traffic_for_path_in_timeslot = {}
        for path_id in range(len(flow_allocations)):
            traffic_for_path_in_timeslot[path_id] = defaultdict(float)
            for request_id in range(len(flow_allocations[path_id])):
                for timeslot in range(len(flow_allocations[path_id][request_id])):
                    traffic_for_path_in_timeslot[path_id][timeslot] += \
                            flow_allocations[path_id][request_id][timeslot]

        return {path_id: [rate for rate in timeslot_to_rate.values()] 
                for path_id, timeslot_to_rate in traffic_for_path_in_timeslot.items()}

    @staticmethod
    def prune_path_capacity_list(path_capacities):
        capacity_for_path_in_timeslot = {}
        for path_id in range(len(path_capacities)):
            capacity_for_path_in_timeslot[path_id] = path_capacities[path_id]
        return capacity_for_path_in_timeslot

    @staticmethod
    def from_solver_file(path_like, id_to_dpid, network_topology):
        with open(path_like, "rb") as fd:
            trial_parameters = pickle.load(fd)

        # flow_allocations :: path_id -> timeslot_number -> tx_rate
        flow_allocations = TuitiTrial.prune_flow_allocations_list(trial_parameters.flow_allocations, 
                trial_parameters.flow_admissions)
        path_capacities = TuitiTrial.prune_path_capacity_list(trial_parameters.path_capacities)

        source_node, destination_node = (0, 1)
        disjoint_paths = list(node_disjoint_paths(network_topology, source_node, destination_node))
        if len(disjoint_paths) < trial_parameters.number_of_paths:
            raise ValueError((f"Not enough paths in the network to conduct the trial. "
                              f"Trial requests {trial_parameters.number_of_paths} but the network "
                              f"only has {len(disjoint_paths)} paths"))

        flow_set = trial.FlowSet()
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

        if isinstance(trial_parameters, EbTrialParameters):
            the_trial.add_parameter("confidence-interval", trial_parameters.confidence_interval)

        for path_id, tx_rate_list in flow_allocations.items():
            the_flow = trial.Flow(source_node, destination_node, tx_rate_list, disjoint_paths,
                    [0]*trial_parameters.number_of_paths)
            flow_set.add_flow(the_flow)
        the_trial.add_parameter("flow-set", flow_set)

        background_traffic_flow_set = trial.FlowSet()
        for path_id, tx_rate_list in path_capacities.items():
            the_flow = trial.Flow(source_node, destination_node, tx_rate_list, disjoint_paths, 
                    [0]*trial_parameters.number_of_paths)
            background_traffic_flow_set.add_flow(the_flow)
        the_trial.add_parameter("background-traffic-flow-set", background_traffic_flow_set)

        return the_trial

    @staticmethod
    def batch_from_directory(path_like, id_to_dpid, network_topology):
        trials = []
        for trial_file in (f for f in path_like.iterdir() if f.is_file() and f.suffix == ".p"):
            trials.append(TuitiTrial.from_solver_file(trial_file, id_to_dpid, network_topology))
        return trials

