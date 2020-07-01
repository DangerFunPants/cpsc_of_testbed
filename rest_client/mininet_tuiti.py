# python3 standard library imports
import time                             as time
import pprint                           as pp
import pathlib                          as path
import traceback                        as traceback
import sys                              as sys
import copy                             as pycopy
from collections                        import defaultdict

# Libraries installed via pip
import numpy                            as np
import networkx                         as nx
import progressbar                      as progressbar

from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths

# Local Imports
import nw_control.trial_provider        as trial_provider
import nw_control.topo_mapper           as topo_mapper
import nw_control.params                as cfg
import nw_control.stat_monitor          as stat_monitor
import tuiti.config                     as tuiti_config
from nw_control.results_repository      import ResultsRepository
from nw_control.host_mapper             import MininetHostMapper
from nw_control.host_rewrite            import Host, MininetHost
from tuiti.tuiti_trial                  import TuitiTrial

import mp_routing.onos_route_adder      as onos_route_adder

def build_n_paths_networkx_graph(number_of_paths):
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])

    for switch_id in range(2, number_of_paths+2):
        graph.add_edge(0, switch_id)
        graph.add_edge(1, switch_id)
    return graph

EXPECTED_TOPO = build_n_paths_networkx_graph(5)

def build_mininet_test_trial_provider():

    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    source_node, destination_node = (0, 1) 
    print(source_node, destination_node)
    disjoint_paths = list(node_disjoint_paths(EXPECTED_TOPO, source_node, destination_node))
    the_trial_provider = trial_provider.TrialProvider("mininet-trial")
    flow_set = trial_provider.FlowSet()
    the_trial = trial_provider.Trial("mininet-test")
    the_trial.add_parameter("duration", 120)

    flow_tx_rate = 131072 * 100
    the_flow = trial_provider.Flow( source_node        = source_node
                                  , destination_node   = destination_node
                                  , flow_tx_rate       = flow_tx_rate
                                  , paths              = disjoint_paths
                                  , splitting_ratio    = [1.0] + [0]*(len(disjoint_paths)-1)
                                  )
    flow_set.add_flows([the_flow])
    the_trial.add_parameter("seed-number", 0)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("traffic-sampling-distribution", "uniform")
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def build_tuiti_trial_provider():
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    source_node, destination_node = (0, 1)
    disjoint_paths = list(node_disjoint_paths(EXPECTED_TOPO, source_node, destination_node))
    the_trial_provider = trial_provider.TrialProvider("tuiti-trial-provider")
    trial_file_directory = path.Path("/home/alexj/repos/inter-dc/trial-parameters/")
    trials = TuitiTrial.batch_from_directory(trial_file_directory, id_to_dpid, EXPECTED_TOPO)
    for the_trial in [t for t in trials 
            # if t.get_parameter("maximum-bandwidth-variation") == 50
            # and t.name == "eb-99"
            ]:
        the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def create_mininet_hosts(id_to_dpid, host_ids):
    host_mapper = MininetHostMapper()
    hosts = {}
    for host_id in host_ids:
        switch_dpid = id_to_dpid[host_id]
        host_ip = host_mapper.get_ip_of_connected_host(switch_dpid)
        # print(f"IP of host connected to {switch_dpid} is {host_ip}")
        hosts[host_id] = MininetHost(host_ip, f"h{host_id}", "alexj", "password", host_id, host_mapper)
    return hosts

def collect_end_host_results(hosts):
    results_map = {}
    for host_id, host in hosts.items():
        receiver_results = host.get_receiver_results()
        try:
            sender_results = host.get_sender_results()
        except ValueError:
            sender_results = None
            
        results_dict = { "receiver" : receiver_results
                       , "sender"   : sender_results
                       }
        results_map[host_id] = results_dict
    return results_map

def scale_flow_tx_rate(normalized_flow_tx_rate):
    """
    Converts from a unitless normalized flow tx rate in the range [0.0, 1.0)
    to a scaled flow tx rate in bytes per second. The rate returned will be 
    in the range [0.0, 10.0) Mbps.
    """
    return (normalized_flow_tx_rate * 10**7) / 8.0

def simple_paths_to_flow_json(simple_paths, tag_values, id_to_dpid):
    path_dicts = []
    tag_values_for_flow = []
    for path in simple_paths:
        source_node         = path[0]
        destination_node    = path[-1]
        path_dict = { "nodes"           : [id_to_dpid[p_i] for p_i in path]
                    , "tagValue"        : tag_values[source_node, destination_node]
                    }
        tag_values_for_flow.append(tag_values[source_node, destination_node])
        tag_values[source_node, destination_node] += 1
        path_dicts.append(path_dict)
    # print(f"Source: {source_node}, Destination: {destination_node}")
    flow_json = {"paths": path_dicts}
    return flow_json, tag_values_for_flow

def destroy_all_mininet_hosts(hosts):
    for host in hosts.values():
        host.disconnect()

def remove_all_flows(flow_tokens):
    for flow_token in flow_tokens:
        try:
            onos_route_adder.uninstall_flow(flow_token)
        except Exception as ex:
            print("Failed to remove flow with token %s." % flow_token)
            print(ex)

def conduct_mininet_trial(results_repository, schema_vars, the_trial_provider, the_trial):
    hosts                           = {}
    flow_allocation_seed_number     = the_trial.get_parameter("seed-number")
    flows                           = the_trial.get_parameter("flow-set")
    flow_tokens                     = set()
    tag_values                      = defaultdict(int)

    try:
        id_to_dpid  = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
        # pp.pprint(id_to_dpid)
        hosts       = create_mininet_hosts(id_to_dpid, [0, 1])

        for host in hosts.values():
            host.start_traffic_generation_server()
            # print(f"PID of server on host with IP {host.host_ip} is {host.server_proc.pid}")
        
        k_matrix = [0.0]*len(flows)
        for flow_id, flow in enumerate(flows):
            source, destination_node, flow_tx_rate_list = (flow.source_node, flow.destination_node, 
                    flow.flow_tx_rate)
            flow_json, tag_values_for_flow = simple_paths_to_flow_json(flow.paths, tag_values, id_to_dpid)
            flow_token = onos_route_adder.install_flow(flow_json)
            flow_tokens.add(flow_token)

            # k_matrix is the splitting ratio
            # tag_values indicate which DSCP tag to use for the path. I think we want a K-matrix that looks
            # kind of like this:
            #
            #                                           1 0 0 0 0
            #                                           0 1 0 0 0
            #                                           0 0 1 0 0
            #                                           0 0 0 1 0
            #                                           0 0 0 0 1
            k_matrix[flow_id] = 1.0
            hosts[flow.source_node].configure_flow_with_precomputed_transmit_rates(
                    flow_tx_rate_list, hosts[flow.destination_node].host_ip, 50000, 
                    pycopy.copy(k_matrix), hosts[flow.source_node].host_id, 
                    1, tag_values_for_flow, flow_id)
            k_matrix[flow_id] = 0.0

            # print(f"Flow source node: {flow.source_node}. Flow destination node: {flow.destination_node}")
            # print(f"Flow source IP: {hosts[flow.source_node].host_ip}, Flow destination IP: {hosts[flow.destination_node].host_ip}")

        for flow_id, background_flow in enumerate(the_trial.get_parameter("background-traffic-flow-set")):
            source, destination, flow_tx_rate_list = (background_flow.source_node, 
                    background_flow.destination_node, background_flow.flow_tx_rate)
            # @TODO: Another thing I need to think about is whether I should have separate flow rules
            #        (i.e. separate DSCP values) for the foreground and background traffic. I don't think
            #        that it would be necessary to have them but it might be useful as it would allow me 
            #        to use ONOS to monitor transmission rates of background and foreground traffic separately.
            #        Might be able to do that with port numbers too but that would probably be more difficult/
            #        annoying. As an alternative the traffic generation clients will record the number of packtes
            #        for foreground and background traffic but you can only calculate average transmit rate
            #        over the course of the entire flow, not on a per timeslot basis.
            # flow_json, tag_values_for_flow = simple_paths_to_flow_json(flow.paths, tag_values, id_to_dpid)
            # flow_token = onos_route_adder.install_flow(flow_json)
            # flow_tokens.add(flow_token)

            # @TODO: I think the values that I'm getting from the solver are actually link capacity,
            #        not the volume of background traffic. So rather than using those values directly 
            #        to compute a transmit rate, I need to compute (link_capacity - value_from_solver)
            #        and then use that to derive a transmission rate. 
            k_matrix[flow_id] = 1.0
            hosts[background_flow.source_node].configure_flow_with_precomputed_transmit_rates(
                    flow_tx_rate_list, hosts[background_flow.destination_node].host_ip, 50000,
                    pycopy.copy(k_matrix), hosts[background_flow.source_node].host_id,
                    1, tag_values_for_flow, flow_id)
            k_matrix[flow_id] = 0.0


        # print(f"Tag values:\n{tag_values_for_flow}")
        time.sleep(10)
        traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
        traffic_monitor.start_monitor()

        for host in hosts.values():
            host.start_traffic_generation_client()

        traffic_generation_pid = hosts[0].client_proc.pid
        print(f"PID of traffic generation process: {traffic_generation_pid}")  
        for idx in progressbar.progressbar(range(int(the_trial.get_parameter("duration")))):
            time.sleep(1.0)
        # input("Press enter to continue...")

        for host in hosts.values():
            host.stop_traffic_generation_client()

        for host in hosts.values():
            host.stop_traffic_generation_server()

        traffic_monitor.stop_monitor()
        
        utilization_results = traffic_monitor.get_monitor_statistics()
        link_utilization_over_time = stat_monitor.compute_link_utilization_over_time(utilization_results)
        mean_link_utilization = stat_monitor.compute_mean_link_utilization(utilization_results)
        end_host_results = collect_end_host_results(hosts)
        path.Path("./mean-link-utilization.txt").write_text(pp.pformat(mean_link_utilization))
        path.Path("./raw-utilization-results.txt").write_text(pp.pformat(utilization_results))
        path.Path("./host-utilization-results.txt").write_text(pp.pformat(end_host_results))

        the_trial.add_parameter("byte-counts-over-time", utilization_results)
        the_trial.add_parameter("link-utilization-over-time", link_utilization_over_time)
        the_trial.add_parameter("measured-link-utilization", mean_link_utilization)
        the_trial.add_parameter("end-host-results", end_host_results)
    except Exception as ex:
        print(ex)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
    finally:
        destroy_all_mininet_hosts(hosts)
        remove_all_flows(flow_tokens)
    
def main():
    results_repository = ResultsRepository.create_repository(tuiti_config.base_repository_path,
            tuiti_config.repository_schema, tuiti_config.repository_name)
    trial_provider = build_tuiti_trial_provider()
    total_trials = len(trial_provider)
    schema_vars = {"provider-name": trial_provider.provider_name}
    for trial_idx, the_trial in enumerate(trial_provider):
        flow_count = len(the_trial.get_parameter("flow-set"))
        print(f"Trial {the_trial.name} has {flow_count} flow(s)")
        print(f"Executing trial {trial_idx+1} out of {total_trials}")
        conduct_mininet_trial(results_repository, schema_vars, trial_provider, the_trial)
        time.sleep(30)
    results_repository.write_trial_provider(schema_vars, trial_provider, overwrite=True)

def test_main():
    results_repository = None
    trial_provider = build_mininet_test_trial_provider()
    for the_trial in trial_provider:
        flow_count = len(the_trial.get_parameter("flow-set"))
        print(f"Trial {the_trial.name} has {flow_count} flow(s)")
        conduct_test_mininet_trial(results_repository, the_trial)

def serialization_testing():
    dir_path = path.Path("/home/alexj/repos/inter-dc/trial-parameters")
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    trials = TuitiTrial.batch_from_directory(dir_path, id_to_dpid, EXPECTED_TOPO)
    for trial in trials:
        # if trial.name == "eb":
        #     confidence_interval = trial.get_parameter("confidence-interval")
        #     print(f"confidence interval is {confidence_interval}")
        print("Mean demand: %s" % trial.get_parameter("mean-flow-demand"))
        if trial.name == "ts":
            sample_flow = next(iter(trial.get_parameter("flow-set")))
            print(sample_flow.flow_tx_rate)

    pp.pprint([trial.name for trial in trials])

def looking_at_trials():
    trial_provider = build_tuiti_trial_provider()
    the_trial = next(iter(trial_provider))
    for the_trial in trial_provider:
        print(f"*************************************** {the_trial.name} ******************************************")
        flow_count = len(the_trial.get_parameter("flow-set"))
        background_flow_count = len(the_trial.get_parameter("background-traffic-flow-set"))
        number_of_admitted_flows = the_trial.get_parameter("number-of-admitted-flows")
        number_of_successful_flows = the_trial.get_parameter("number-of-successful-flows")
        print(f"Number of flows: {flow_count}")
        print(f"Number of admitted flows: {number_of_admitted_flows}")
        print(f"Number of successful flows: {number_of_successful_flows}")
        print(f"Flow success rate: {number_of_successful_flows / number_of_admitted_flows}")
        print(f"Number of background flows: {background_flow_count}")
        number_of_timeslots = the_trial.get_parameter("number-of-timeslots")
        print(f"Number of timeslots: {number_of_timeslots}")
        timeslot_duration = the_trial.get_parameter("timeslot-duration")
        print(f"Timeslot duration: {timeslot_duration}")
        maximum_variation = the_trial.get_parameter("maximum-bandwidth-variation")
        print(f"Maximum variation: {maximum_variation}")
        trial_duration = number_of_timeslots * timeslot_duration

        tx_rates = []
        bulk_transfer_total_volume = 0.0
        for flow in the_trial.get_parameter("flow-set"):
            bulk_transfer_total_volume += sum(flow.flow_tx_rate)

        background_traffic_total_volume = 0.0
        for flow in the_trial.get_parameter("background-traffic-flow-set"):
            background_traffic_total_volume += sum(flow.flow_tx_rate)
        
        total_volume = bulk_transfer_total_volume + background_traffic_total_volume
        mean_tx_rate = (total_volume * 8) / (number_of_timeslots * timeslot_duration * 2**20)
        duration_of_trial_in_minutes = (trial_duration) / 60
        print(f"Total transmission volume: {total_volume}")
        print(f"Mean transmission rate: {mean_tx_rate} Mibps")
        print(f"Duration of trial: {duration_of_trial_in_minutes}")
        
        bulk_transfer_mean_tx_rate = (bulk_transfer_total_volume * 8) / (trial_duration * 2**20)
        print(f"Mean transmission rate of bulk transfers: {bulk_transfer_mean_tx_rate}")
        background_traffic_mean_tx_rate = (background_traffic_total_volume * 8) / (trial_duration * 2**20)
        print(f"Mean transmission rate of background traffic: {background_traffic_mean_tx_rate}")

        bulk_transfer_proportion = bulk_transfer_total_volume / total_volume
        print(f"Bulk transfer proportion: {bulk_transfer_proportion}")
        background_traffic_proportion = background_traffic_total_volume / total_volume
        print(f"Background traffic proportion: {background_traffic_proportion}")

        for flow_idx, flow in enumerate(the_trial.get_parameter("flow-set")):
            total_volume_for_flow = sum(flow.flow_tx_rate)
            mean_tx_rate_for_flow = (total_volume_for_flow * 8) / (trial_duration * 2**20)
            number_of_negative_transmission_rates = \
                    len([tx_rate for tx_rate in flow.flow_tx_rate if tx_rate < 0])
            print(f"Mean transmission rate for bulk transfers on path {flow_idx}: {mean_tx_rate_for_flow}",
                    f"Number of negative transmission rates: {number_of_negative_transmission_rates}")
        print("")

        for flow_idx, flow in enumerate(the_trial.get_parameter("background-traffic-flow-set")):
            total_volume_for_flow = sum(flow.flow_tx_rate)
            mean_tx_rate_for_flow = (total_volume_for_flow * 8) / (trial_duration * 2**20)
            number_of_negative_transmission_rates = \
                    len([tx_rate for tx_rate in flow.flow_tx_rate if tx_rate < 0])
            print(f"Mean transmission rate for real time traffic on path {flow_idx}: {mean_tx_rate_for_flow}",
                    f"Number of negative transmission rates: {number_of_negative_transmission_rates}")
        print("\n")

        for path_idx, path_capacities in enumerate(the_trial.get_parameter("remaining-capacities")):
            total_remaining_capacity = sum(path_capacities)
            mean_remaining_capacity = (total_remaining_capacity * 8) / (trial_duration * 2**20)
            print(f"Mean remaining capacity on path {path_idx}: {mean_remaining_capacity}")

        print(f"***************************************************************************************************")

def conduct_test_mininet_trial(results_reposity, the_trial):
    hosts                           = {}
    flow_allocation_seed_number     = the_trial.get_parameter("seed-number")
    flows                           = the_trial.get_parameter("flow-set")
    flow_tokens                     = set()
    tag_values                      = defaultdict(int)

    try:
        id_to_dpid  = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
        pp.pprint(id_to_dpid)
        hosts       = create_mininet_hosts(id_to_dpid, [0, 1])

        for host in hosts.values():
            host.start_traffic_generation_server()
            # print(f"PID of server on host with IP {host.host_ip} is {host.server_proc.pid}")
        
        source_node, destination_node = (0, 1)
        flow_rate_list = [1310720]*300
        hosts[source_node].configure_flow_with_precomputed_transmit_rates(flow_rate_list,
                hosts[destination_node].host_ip, 50000, [1.0, 0.0, 0.0, 0.0, 0.0], hosts[source_node].host_id,
                10, [0, 0, 0, 0, 0])
        # for flow_id, flow in enumerate(flows):
        #     source_node, destination_node, flow_tx_rate = (flow.source_node, flow.destination_node,
        #             flow.flow_tx_rate)
        #     flow_json, tag_values_for_flow = simple_paths_to_flow_json(flow.paths, tag_values, id_to_dpid)
        #     flow_token = onos_route_adder.install_flow(flow_json)
        #     flow_tokens.add(flow_token)

        #     # ======================================= For Testing ======================================= 
        #     hosts[flow.source_node].configure_flow(flow.flow_tx_rate, 0.0, 
        #         the_trial.get_parameter("traffic-sampling-distribution"), hosts[flow.destination_node].host_ip,
        #         50000, [1.0] + [0.0]*(len(flow.paths)-1), 100, [0]*len(flow.paths))
        #     # ======================================= End Testing ======================================= 


        # print(f"Tag values:\n{tag_values_for_flow}")
        time.sleep(10)
        traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
        traffic_monitor.start_monitor()

        for host in hosts.values():
            host.start_traffic_generation_client()
        
        traffic_generation_client_pid = hosts[0].client_proc.pid
        print(f"PID of traffic generation client: {traffic_generation_client_pid}")

        # print(f"Trial duration is {the_trial.get_parameter('duration')}")
        # time.sleep(the_trial.get_parameter("duration"))
        # time.sleep(300)
        input("Press enter to continue...")

        for host in hosts.values():
            host.stop_traffic_generation_client()

        for host in hosts.values():
            host.stop_traffic_generation_server()

        traffic_monitor.stop_monitor()
        
        utilization_results = traffic_monitor.get_monitor_statistics()
        link_utilization_over_time = stat_monitor.compute_link_utilization_over_time(utilization_results)
        mean_link_utilization = stat_monitor.compute_mean_link_utilization(utilization_results)
        end_host_results = collect_end_host_results(hosts)
        path.Path("./mean-link-utilization.txt").write_text(pp.pformat(mean_link_utilization))
        path.Path("./raw-utilization-results.txt").write_text(pp.pformat(utilization_results))
        path.Path("./host-utilization-results.txt").write_text(pp.pformat(end_host_results))
        pp.pprint(end_host_results)

        the_trial.add_parameter("byte-counts-over-time", utilization_results)
        # pp.pprint(utilization_results)
    except Exception as ex:
        print(ex)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
    finally:
        destroy_all_mininet_hosts(hosts)
        remove_all_flows(flow_tokens)
    
if __name__ == "__main__":
    main()
    # test_main()
    # serialization_testing()
    # looking_at_trials()
