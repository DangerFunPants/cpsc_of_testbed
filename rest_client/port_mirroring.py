
import pathlib              as path
import pprint               as pp
import json                 as json
import requests             as req
import urllib.parse         as url
import time                 as time

import nw_control.params                        as cfg
import nw_control.topo_mapper                   as topo_mapper
import nw_control.host_mapper                   as host_mapper
import nw_control.host                          as host
import nw_control.stat_monitor                  as stat_monitor
import port_mirroring.params                    as pm_cfg
import data_visualization.link_utilization      as link_utilization

from collections            import namedtuple
from sys                    import argv

FlowDefinition          = namedtuple("FlowDefinition", "flow_id traffic_rate, path")
SwitchDefinition        = namedtuple("SwitchDefinition", "switch_id resident_flows")
SolutionDefinition      = namedtuple("SolutionDefinition", "flow_id mirror_switch_id")

def parse_flows_from_file(file_path):
    with file_path.open("r") as fd:
        lines = fd.readlines()
    flows = {}
    for line in lines:
        tokens = line.split(" ")
        [flow_id, traffic_rate], path = tokens[:2], tokens[2:]
        flow_id = int(flow_id)
        traffic_rate = float(traffic_rate)
        path = [int(node_id) for node_id in path]
        flow_def = FlowDefinition(flow_id, traffic_rate, path)
        flows[flow_id] = flow_def

    return flows
        
def parse_switches_from_file(file_path):
    with file_path.open("r") as fd:
        lines = fd.readlines()
    switches = {}
    for line in lines:
        tokens = line.split(" ")
        [[switch_id], resident_flows] = tokens[:1], tokens[1:]
        switch_id = int(switch_id)
        resident_flows = [int(flow_id) for flow_id in resident_flows]
        switch_def = SwitchDefinition(switch_id, resident_flows)
        switches[switch_id] = switch_def

    return switches

def parse_solutions_from_file(file_path):
    with file_path.open("r") as fd:
        lines = fd.readlines()
    solutions = {}
    for line in lines[:-1]:
        [flow_id, mirror_switch_id] = line.split(" ")
        flow_id = int(flow_id)
        mirror_switch_id = int(mirror_switch_id)
        solution_def = SolutionDefinition(flow_id, mirror_switch_id)
        solutions[flow_id] = solution_def

    return solutions

def create_add_mirroring_rules_request_json(flow_def, switches, solution_def, id_to_dpid, tag_value):
    def create_path_json(flow_def):
        path_json_dict = {"nodes": [id_to_dpid[node_id] for node_id in flow_def.path]}
        return path_json_dict

    json_dict = { "mirrorSwitch"        : id_to_dpid[solution_def.mirror_switch_id]
                , "tagValue"            : tag_value
                , "flowRoute"           : create_path_json(flow_def)
                }
    return json.dumps(json_dict)

def request_port_mirroring(flow_def, switches, solution_def, id_to_dpid, tag_value):
    json_body = create_add_mirroring_rules_request_json(flow_def, switches, solution_def, id_to_dpid, tag_value)
    # rest_endpoint = "http://127.0.0.1:8181/onos/port-mirroring/v1/add-mirrored-flow"
    rest_endpoint = url.urljoin(cfg.onos_url.geturl(), "port-mirroring/v1/add-mirrored-flow")
    print(rest_endpoint)
    port_mirroring_request = req.post(rest_endpoint, data=json_body, auth=cfg.ONOS_API_CREDENTIALS)
    if port_mirroring_request.status_code != 200:
        pp.pprint(port_mirroring_request.text)
        raise ValueError("add-mirrored-flow request failed with code %d %s" % 
                (port_mirroring_request.status_code, port_mirroring_request.reason))
    else:
        print("Successfully added mirrored flow")
        response = json.loads(port_mirroring_request.text)
        pp.pprint(response)
        return response["routeId"]

def remove_port_mirroring_rules(flow_token):
    rest_endpoint = url.urljoin(cfg.onos_url.geturl(), "port-mirroring/v1/remove-mirrored-flow") + ("?route-id=%s" % flow_token)
    remove_mirroring_rules_request = req.post(rest_endpoint, auth=cfg.ONOS_API_CREDENTIALS)
    if remove_mirroring_rules_request.status_code != 200:
        pp.pprint(remove_mirroring_rules_request.text)
        raise ValueError("remove-mirrored-flow request failed with code %d %s" %
                (remove_mirroring_rules_request.status_code, remove_mirroring_rules_request.reason))
    else:
        print("Successfully removed mirrored flow with ID %s" % flow_token)

def add_port_mirroring_flows(topo_file_path, flows, switches, solutions):
    flow_ids_to_add = flows.keys()
    id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo_file_path)
    flow_tokens = {}
    for flow_id in flow_ids_to_add:
        flow_tokens[flow_id] = request_port_mirroring(flows[flow_id], switches, solutions[flow_id], id_to_dpid, flow_id)
    return flow_tokens

def remove_port_mirroring_flows(flow_tokens):
    for flow_token in flow_tokens.values():
        remove_port_mirroring_rules(flow_token)

def create_and_initialize_host_connections(flows):
    mapper = host_mapper.OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port, pm_cfg.target_topo_path)
    host_ids = set()
    for flow in flows.values():
        host_ids.add(flow.path[0])
        host_ids.add(flow.path[-1])

    hosts = {}
    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = host.TrafficGenHost.create_host(hostname)
        hosts[host_id].connect()

    return hosts

def close_all_host_connections(hosts):
    for host in hosts.values():
        host.disconnect()

def conduct_port_mirroring_trial():
    mapper = host_mapper.OnosMapper(cfg.dns_server_ip, cfg.of_controller_ip, 
            cfg.of_controller_port, pm_cfg.target_topo_path)

    flows           = parse_flows_from_file(pm_cfg.flow_file_path)
    switches        = parse_switches_from_file(pm_cfg.switch_file_path)
    solutions       = parse_solutions_from_file(pm_cfg.solution_file_path)

    flow_tokens = add_port_mirroring_flows(pm_cfg.target_topo_path, flows, switches, solutions)

    hosts = create_and_initialize_host_connections(flows)

    destination_hosts = {flow.path[-1] for flow in flows.values()}
    for destination_host in destination_hosts:
        # @TODO: Why do I need to pass the ID to this method. Shouldn't have to 
        # tell the host about itself.
        hosts[destination_host].start_server(destination_host)

    for flow_id, flow in flows.items():
        destination_hostname    = mapper.map_sw_to_host(flow.path[-1])
        tx_rate                 = flow.traffic_rate * 1000000
        tx_variance             = 0.0
        traffic_model           = "uniform"
        destination_ip          = mapper.resolve_hostname(destination_hostname)
        destination_port        = 50000
        k_mat                   = [1.0]
        host_num                = flow.path[0]
        time_slice              = 100
        pkt_len                 = 1066
        tag_value               = flow_id

        hosts[flow.path[0]].configure_client(tx_rate, tx_variance, traffic_model,
                destination_ip, destination_port, k_mat, host_num, time_slice, tag_value, pkt_len)

    traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
    traffic_monitor.start_monitor()

    for source_node in {flow.path[0] for flow in flows.values()}:
        hosts[source_node].start_clients()

    time.sleep(pm_cfg.trial_length)

    traffic_monitor.stop_monitor()

    for host_id in {flow.path[0] for flow in flows.values()}:
        hosts[host_id].stop_client()

    # This probably isn't necessary, presumably it's to let 
    # the network "drain" before killing the server processes 
    # in order to avoid inflated loss rates.
    time.sleep(15) 

    for host_id in {flow.path[-1] for flow in flows.values()}:
        hosts[host_id].stop_server()

    remove_port_mirroring_flows(flow_tokens)
    utilization_results = traffic_monitor.get_monitor_statistics()
    utilization_results_out_path = path.Path("./utilization-results.txt")
    with utilization_results_out_path.open("w") as fd:
        fd.write(json.dumps(utilization_results))

def main():
    link_utilization.main()
    # conduct_port_mirroring_trial()
    # flow_path   = pm_cfg.flow_file_path
    # flows       = parse_flows_from_file(flow_path)
    # hosts = create_and_initialize_host_connections(flows)
    # input("Press enter to close host connections...")
    # close_all_host_connections(hosts)

    # if len(argv) == 1:
    #     add_port_mirroring_flows()
    # else:
    #     topo_path = pm_cfg.target_topo_path
    #     id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo_path)
    #     dpid_to_id = {v: k for k, v in id_to_dpid.items()}
    #     for dpid in argv[1:]:
    #         print("DPID %s maps to %d" % (dpid, dpid_to_id.get(dpid, "UNKNOWN")))

    # topo_path = INPUT_FILE_DIR.joinpath("network/topo")
    # try:
    #     id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo_path)
    # except ValueError:
    #     print("Network topo is incorrect.")
    #     return 
    # print("Network topo is correct.")

    # topo_path   = INPUT_FILE_DIR.joinpath("network/topo")
    # flow_path   = INPUT_FILE_DIR.joinpath("network/flows")
    # flows       = parse_flows_from_file(flow_path)

    # nw_invalid_edges     = topo_mapper.verify_flows_against_nw_topo(topo_path, flows)
    # target_invalid_edges = topo_mapper.verify_flows_against_target_topo(topo_path, flows)

    # if nw_invalid_edges != target_invalid_edges:
    #     print("Target and network are different.")
    #     print("Network:")
    #     pp.pprint(nw_invalid_edges)
    #     print("Target:")
    #     pp.pprint(target_invalid_edges)
    # else:
    #     print("Flows do not correspond to topologies in the same way.")

if __name__ == "__main__":
    main()