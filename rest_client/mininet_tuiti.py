

# python3 standard library imports
import time                             as time
import pprint                           as pp
import pathlib                          as path
import traceback                        as traceback
import sys                              as sys
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
from nw_control.results_repository      import ResultsRepository
from nw_control.host_mapper             import MininetHostMapper
from nw_control.host_rewrite            import Host, MininetHost

import mp_routing.onos_route_adder      as onos_route_adder



EXPECTED_TOPO = nx.complete_graph(2)

class Flow:
    """
    Represents a flow with 
        * Source node
        * Destination node
        * Transmission rate
        * A set of paths through the substrate network. 
    """
    def __init__( self
                , source_node       = None
                , destination_node  = None
                , flow_tx_rate      = None
                , paths             = None
                , splitting_ratio   = None):
        self._source_node       = source_node
        self._destination_node  = destination_node
        self._flow_tx_rate      = flow_tx_rate
        self._paths             = paths
        self._splitting_ratio   = splitting_ratio

    @property
    def source_node(self):
        return self._source_node

    @property
    def destination_node(self):
        return self._destination_node

    @property
    def flow_tx_rate(self):
        return self._flow_tx_rate

    @property
    def paths(self):
        return self._paths

    @property
    def splitting_ratio(self):
        return self._splitting_ratio

class FlowSet:
    """
    Encapsulates a set of flows. Typically the set of flows will comprise a trial.
    """
    def __init__(self):
        self._flows     = []

    @property
    def flows(self):
        return self._flows

    def add_flow(self, flow):
        self._flows.append(flow)

    def add_flows(self, flows):
        self._flows.extend(flows)

    def __iter__(self):
        for flow in self.flows:
            yield flow

    def __str__(self):
        s = "Flow set with %d flows." % len(self.flows)
        return s

    def __len__(self):
        return len(self.flows)

def build_mininet_test_trial_provider():

    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(EXPECTED_TOPO)
    source_node, destination_node = (0, 1) 
    print(source_node, destination_node)
    disjoint_paths = list(node_disjoint_paths(EXPECTED_TOPO, source_node, destination_node))
    the_trial_provider = trial_provider.TrialProvider("mininet-trial")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("mininet-test")
    the_trial.add_parameter("duration", 10)

    flow_tx_rate = 0.5
    the_flow = Flow( source_node        = source_node
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

def create_mininet_hosts(id_to_dpid):
    host_mapper = MininetHostMapper()
    hosts = {}
    for host_id, switch_dpid in id_to_dpid.items():
        host_ip = host_mapper.get_ip_of_connected_host(switch_dpid)
        print(f"IP of host connected to {switch_dpid} is {host_ip}")
        hosts[host_id] = MininetHost(f"h{host_id}", "alexj", "password", host_id, host_mapper)
    return hosts

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
    pass

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
        hosts       = create_mininet_hosts(id_to_dpid)

        for host in hosts.values():
            host.start_traffic_generation_server()
        
        for flow in flows:
            source, destination_node, flow_tx_rate = (flow.source_node, flow.destination_node, 
                    flow.flow_tx_rate)
            flow_json, tag_values_for_flow = simple_paths_to_flow_json(flow.paths, tag_values, id_to_dpid)
            flow_token = onos_route_adder.install_flow(flow_json)
            flow_tokens.add(flow_token)

            # Probably won't use this for now but it might be handy later. 
            scaled_flow_tx_rate = scale_flow_tx_rate(flow_tx_rate)
            hosts[flow.destination_node].configure_flow(scaled_flow_tx_rate, 0.0, "uniform",
                    hosts[flow.source_node].host_ip, 50000, flow.splitting_ratio, 1, tag_values_for_flow)

             
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
        the_trial.add_parameter("byte-counts-over-time", utilization_results)
        pp.pprint(utilization_results)
    except Exception as ex:
        print(ex)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=3, file=sys.stdout)
    finally:
        destroy_all_mininet_hosts(hosts)
        remove_all_flows(flow_tokens)
    
def main():
    results_repository = None
    trial_provider = build_mininet_test_trial_provider()
    for the_trial in trial_provider:
        flow_count = len(the_trial.get_parameter("flow-set"))
        conduct_mininet_trial(results_repository, the_trial)
        print(f"Trial {the_trial.name} has {flow_count} flow(s)")

def host_testing():
    try:
        mapper = MininetHostMapper()
        h1 = MininetHost("h1", "alexj", "password", 1, mapper)
        h2 = MininetHost("h2", "alexj", "password", 2, mapper)
        input("Created hosts...")

        h1.start_traffic_generation_server()
        print(f"PID of traffic_server process is {h1.server_proc.pid}")
        input("Press enter to start client process...")

        h2.configure_flow(131072, 0, "uniform", "10.0.0.1", 50000, [1.0], 50, [0])
        h2.start_traffic_generation_client()
        print(f"PID of traffic_gen process is {h2.client_proc.pid}")
        input("Press enter to shut everything down...")

        h2.stop_traffic_generation_client()
        h1.stop_traffic_generation_server()
        print("Stopped traffic generation server...")

        print("h2 output:")
        print(h2.client_proc.read_stderr())
    except Exception as ex:
        print(f"Failed:\n{ex}")
        h1.stop_traffic_generation_server()
        h2.stop_traffic_generation_client()

if __name__ == "__main__":
    main()
    # host_testing()
