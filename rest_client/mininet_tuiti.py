# python3 standard library imports
import time                             as time
import pprint                           as pp
import pathlib                          as path
import traceback                        as traceback
import sys                              as sys
import copy                             as pycopy
import pickle                           as pickle           # @TODO: This shouldn't be here.
from collections                        import defaultdict

# Libraries installed via pip
import numpy                            as np
import networkx                         as nx

from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths

# Local Imports
import nw_control.trial_provider        as trial_provider
import nw_control.topo_mapper           as topo_mapper
import nw_control.params                as cfg
import nw_control.stat_monitor          as stat_monitor
import tuiti.tuiti_trial                as tuiti_trial
from nw_control.results_repository      import ResultsRepository
from nw_control.host_mapper             import MininetHostMapper
from nw_control.host_rewrite            import Host, MininetHost

import mp_routing.onos_route_adder      as onos_route_adder

# EXPECTED_TOPO = nx.complete_graph(2)

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
    the_trial.add_parameter("duration", 10)

    flow_tx_rate = 0.5
    the_flow = trial_provider.Flow( source_node        = source_node
                                  , destination_node   = destination_node
                                  , flow_tx_rate       = flow_tx_rate
                                  , paths              = disjoint_paths
                                  , splitting_ratio    = [1.0] + [0]*(len(disjoint_paths)-1)
                                  )
    flow_set.add_flows([the_flow])
    the_trial.add_parameter("seed-number", 0)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def build_tuiti_trial_provider():
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    source_node, destination_node = (0, 1)
    disjoint_paths = list(node_disjoint_paths(EXPECTED_TOPO, source_node, destination_node))
    the_trial_provider = trial_provider.TrialProvider("tuiti-trial-provider")
    flow_set = trial_provider.FlowSet()
    the_trial = tuiti_trial.TuitiTrial.from_solver_file(path.Path(
        "/home/alexj/repos/inter-dc/trial-parameters/average.p"), id_to_dpid, EXPECTED_TOPO)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def create_mininet_hosts(id_to_dpid, host_ids):
    host_mapper = MininetHostMapper()
    hosts = {}
    for host_id in host_ids:
        switch_dpid = id_to_dpid[host_id]
        host_ip = host_mapper.get_ip_of_connected_host(switch_dpid)
        print(f"IP of host connected to {switch_dpid} is {host_ip}")
        hosts[host_id] = MininetHost(f"h{host_id}", "alexj", "password", host_id, host_mapper)
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

def conduct_mininet_trial(results_repository, the_trial):
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
        
        k_matrix = [0.0]*len(flows)
        for flow_id, flow in enumerate(flows):
            source, destination_node, flow_tx_rate = (flow.source_node, flow.destination_node, 
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
            print(f"k-matrix: {k_matrix}")
            hosts[flow.destination_node].configure_flow_with_precomputed_transmit_rates(
                    [x*10 for x in flow_tx_rate], hosts[flow.source_node].host_ip, 50000, pycopy.copy(k_matrix), 
                    hosts[flow.destination_node].host_id, the_trial.get_parameter("timeslot-duration"), 
                    tag_values_for_flow)
            k_matrix[flow_id] = 0.0

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
            hosts[background_flow.destination_node].configure_flow_with_precomputed_transmit_rates(
                    [x*10 for x in flow_tx_rate], hosts[background_flow.source_node].host_ip, 50000,
                    pycopy.copy(k_matrix), hosts[background_flow.destination_node].host_id,
                    1, tag_values_for_flow)
            k_matrix[flow_id] = 0.0


        print(f"Tag values:\n{tag_values_for_flow}")
        traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
        traffic_monitor.start_monitor()

        for host in hosts.values():
            host.start_traffic_generation_client()

        # time.sleep(the_trial.get_parameter("duration"))
        input("Press enter to continue...")

        for host in hosts.values():
            host.stop_traffic_generation_client()

        for host in hosts.values():
            host.stop_traffic_generation_server()

        traffic_monitor.stop_monitor()
        
        utilization_results = traffic_monitor.get_monitor_statistics()
        end_host_results = collect_end_host_results(hosts)
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
    
def main():
    results_repository = None
    # trial_provider = build_mininet_test_trial_provider()
    trial_provider = build_tuiti_trial_provider()
    for the_trial in trial_provider:
        flow_count = len(the_trial.get_parameter("flow-set"))
        print(f"Trial {the_trial.name} has {flow_count} flow(s)")
        conduct_mininet_trial(results_repository, the_trial)

def serialization_testing():
    dir_path = path.Path("/home/alexj/repos/inter-dc/trial-parameters")
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    trials = tuiti_trial.TuitiTrial.batch_from_directory(dir_path, id_to_dpid, EXPECTED_TOPO)
    for trial in trials:
        # if trial.name == "eb":
        #     confidence_interval = trial.get_parameter("confidence-interval")
        #     print(f"confidence interval is {confidence_interval}")
        if trial.name == "ts":
            sample_flow = next(iter(trial.get_parameter("flow-set")))
            print(sample_flow.flow_tx_rate)

    pp.pprint([trial.name for trial in trials])

if __name__ == "__main__":
    # main()
    serialization_testing()
