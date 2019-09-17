
import pprint                           as pp
import networkx                         as nx
import itertools                        as itertools
import traceback                        as traceback
import time                             as time
import json                             as json

import virtual_hosts.virtual_host       as virtual_host
import path_hopping.flow_allocation     as flow_allocation
import nw_control.topo_mapper           as topo_mapper
import nw_control.stat_monitor          as stat_monitor
import nw_control.params                as cfg
import mp_routing.onos_route_adder      as onos_route_adder
import path_hopping.params              as ph_cfg
import path_hopping.trials              as ph_trials

from networkx.algorithms.shortest_paths.generic     import all_shortest_paths
from collections                                    import defaultdict

from virtual_hosts.virtual_host                     import TrafficGenerationVirtualHost
from nw_control.results_repository                  import ResultsRepository

TARGET_GRAPH = nx.complete_graph(10)

def create_virtual_hosts(id_to_dpid):
    hosts = {}
    for host_id in range(1, 11):
        virtual_host_mac_address    = "00:02:00:00:00:%02d" % host_id
        actual_host_ip_address      = "192.168.1.%d" % host_id
        virtual_host_ip_address     = "10.10.0.%d" % host_id
        ingress_node_device_id      = id_to_dpid[host_id-1]

        the_virtual_host = TrafficGenerationVirtualHost.create_virtual_host(host_id, 
                virtual_host_mac_address, virtual_host_ip_address, 
                actual_host_ip_address, ingress_node_device_id)
        hosts[host_id] = the_virtual_host

    # Wait until all three ARP replies for each of the hosts have been injected 
    # by the controller.
    time.sleep(10)
    return hosts

def destroy_all_hosts(hosts):
    for host in hosts.values():
        try:
            host.destroy_virtual_host()
        except Exception as ex:
            print("Failed to destroy virtual host %s" % str(host))
            print(ex)

def remove_all_flows(flow_tokens):
    for flow_token in flow_tokens:
        try:
            onos_route_adder.uninstall_flow(flow_token)
        except Exception as ex:
            print("Failed to remove flow with token %s." % flow_token)
            print(ex)

def scale_flow_tx_rate(normalized_flow_tx_rate):
    """
    Converts from a unitless normalized flow tx rate in the range [0.0, 1.0)
    to a scaled flow tx rate in bytes per second. The rate returned will be 
    in the range [0.0, 10.0) Mbps.
    """
    return (normalized_flow_tx_rate * 10**6) / 8.0

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

def conduct_path_hopping_trial(results_repository, the_trial):
    id_to_dpid                      = topo_mapper.get_and_validate_onos_topo_x(TARGET_GRAPH)
    hosts                           = {}
    flow_allocation_seed_number     = the_trial.get_parameter("seed-number")
    flows                           = the_trial.get_parameter("flow-set")
    flow_tokens                     = set()
    tag_values                      = defaultdict(int)

    try:
        hosts = create_virtual_hosts(id_to_dpid)
        for host in hosts.values():
            host.start_traffic_generation_server()

        for flow in flows:
            source_node, destination_node, flow_tx_rate = (flow.source_node, 
                    flow.destination_node, flow.flow_tx_rate)

            flow_json, tag_values_for_flow = simple_paths_to_flow_json(flow.paths, tag_values, 
                    id_to_dpid)
            flow_token = onos_route_adder.install_flow(flow_json)
            flow_tokens.add(flow_token)
            scaled_flow_tx_rate = scale_flow_tx_rate(flow_tx_rate)
            hosts[source_node+1].configure_flow(scaled_flow_tx_rate, 0.0, "uniform",
                    hosts[destination_node+1].virtual_host_ip, 50000, flow.splitting_ratio, 10,
                    tag_values_for_flow)

        traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
        traffic_monitor.start_monitor()
        for host in hosts.values():
            host.start_traffic_generation_client()
        # input("Hosts have been created and flows have been added. Press enter to continue...")
        time.sleep(the_trial.get_parameter("duration"))
        traffic_monitor.stop_monitor()
        utilization_results = traffic_monitor.get_monitor_statistics()
        the_trial.add_parameter("utilization-results", utilization_results)
        

    except Exception as ex:
        traceback.print_exc()
        print(ex)
        input("Failed to carry out path hopping test. Press enter to continue...")
    finally:
        destroy_all_hosts(hosts)
        remove_all_flows(flow_tokens)

def main():
    EXECUTION_MODE = "simulate"
    results_repository = ResultsRepository.create_repository(ph_cfg.base_repository_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)

    # trial_provider = ph_trials.path_hopping_various_k_values(TARGET_GRAPH)
    # trial_provider = ph_trials.single_path_routing(TARGET_GRAPH)
    # trial_provider = ph_trials.path_hopping_flows(TARGET_GRAPH, K=3)
    # trial_provider = ph_trials.flow_allocation_tests(TARGET_GRAPH, 2)
    # trial_provider = ph_trials.attempted_optimal_flows(TARGET_GRAPH, K=3)
    # trial_provider = ph_trials.greedy_path_hopping_flows(TARGET_GRAPH, K=5)
    # trial_provider = ph_trials.path_hopping_mcf_flows(TARGET_GRAPH, K=5)
    # trial_provider = ph_trials.ilp_flows(graph)
    # trial_provider = ph_trials.mcf_flows(graph)
    # trial_provider = ph_trials.multiflow_tests(test_graph, K=5)
    # trial_provider = ph_trials.multiflow_tests_binomial(TARGET_GRAPH)
    # trial_provider = ph_trials.multiflow_tests_uniform(TARGET_GRAPH)
    test_topology = nx.complete_graph(10)
    trial_provider = ph_trials.k_flows_tests(test_topology)
    
    if EXECUTION_MODE == "testbed":
        for the_trial in trial_provider:
            conduct_path_hopping_trial(results_repository, the_trial, trial_provider)
            time.sleep(10)

    elif EXECUTION_MODE == "simulate":
        for the_trial in trial_provider:
            print("Trial %s has %d flows." % (
                the_trial.name, len(the_trial.get_parameter("flow-set"))))
            link_utilization = the_trial.get_parameter("link-utilization")
            # pp.pprint(link_utilization)
            # print(sum(link_utilization.values()))

    schema_vars = { "provider-name"     : trial_provider.provider_name
                  }

    results_repository.write_trial_provider(schema_vars, trial_provider, overwrite=True)

if __name__ == "__main__":
    main()
