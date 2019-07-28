
import json             as json
import urllib.parse     as url
import requests         as req
import pprint           as pp

import nw_control.params            as cfg
import nw_control.topo_mapper       as topo_mapper

from collections import defaultdict

def verify_that_all_flows_are_mirrored(flows, switches, solutions, port_ids_to_port_numbers,
        id_to_dpid):
    mirrored_flow_ids = set()
    for solution_id, solution_list in solutions.items():
        for solution in solution_list:
            switch_id                   = solution.mirror_switch_id
            port_id                     = solution.mirror_switch_port
            mirrored_dpid               = id_to_dpid[switch_id]
            mirrored_port_number        = port_ids_to_port_numbers[port_id]
            for flow_id, flow in flows.items():
                for flow_switch_id, flow_port_id in zip(flow.path, flow.ports):
                    flow_dpid           = id_to_dpid[flow_switch_id]
                    actual_port_number  = port_ids_to_port_numbers[flow_port_id]
                    if (actual_port_number == mirrored_port_number
                            and flow_dpid == mirrored_dpid):
                        mirrored_flow_ids.add(flow_id)

    if len(mirrored_flow_ids) != len(flows):
        print("*************ERROR: All flows have not been mirrored*****************")
    else:
        print("All flows have been mirrored.")

def verify_path_ports(flows_mapped_to_nw):
    for flow_id, flow_mapped_to_nw in flows_mapped_to_nw.items():
        dpid_to_port = {dpid: port_num 
                for dpid, port_num in zip(flow_mapped_to_nw.path, flow_mapped_to_nw.ports)}
        for switch_id, next_hop_id in zip(flow_mapped_to_nw.path, flow_mapped_to_nw.path[1:]):
            source_port, dest_port = topo_mapper.get_ports_that_connect(switch_id, next_hop_id)
            if source_port != dpid_to_port[switch_id]:
                print("WEIRDNESS WITH MAPPING BETWEEN PORT IDS AND PORT NUMBERS.")
                print("Expected dpid %s to have port %s connecting to %s. Found port %s" %
                        (switch_id, dpid_to_port[switch_id], next_hop_id, source_port))


def create_add_flow_mirroring_rules_request_json(flow_def, switches, solution_def, id_to_dpid, tag_value):
    def create_path_json(flow_def):
        path_json_dict = {"nodes": [id_to_dpid[node_id] for node_id in flow_def.path]}
        return path_json_dict

    json_dict = { "mirrorSwitch"        : id_to_dpid[solution_def.mirror_switch_id]
                , "tagValue"            : tag_value
                , "flowRoute"           : create_path_json(flow_def)
                }
    return json.dumps(json_dict)

def create_add_port_mirroring_rules_request_json( flow_def
                                                , switches
                                                , solutions
                                                , id_to_dpid
                                                , tag_value
                                                , port_ids_to_port_numbers):
    def create_path_json(flow_def):
        path_json_dict = {"nodes": [id_to_dpid[node_id] for node_id in flow_def.path]}
        return path_json_dict

    def create_port_numbers_json(flow_def, port_ids_to_port_numbers, id_to_dpid):
        port_numbers = []
        for switch_id, port_id in zip(flow_def.path[:-1], flow_def.ports[:-1]):
            actual_port_number = port_ids_to_port_numbers[switch_id][port_id]
            port_numbers.append(actual_port_number)
        
        last_hop_switch_dpid = id_to_dpid[flow_def.path[-1]]
        last_hop_egress_port = topo_mapper.get_host_port(last_hop_switch_dpid)
        port_numbers.append(last_hop_egress_port)
        return port_numbers

    def create_mirrored_ports_json(solutions, id_to_dpid, port_ids_to_port_numbers):
        mirrored_switch_ports = defaultdict(list)
        for solution_id, solution_list in solutions.items():
            for solution in solution_list:
                actual_port_number = port_ids_to_port_numbers[solution.mirror_switch_id][solution.mirror_switch_port]
                mirror_switch_dpid = id_to_dpid[solution.mirror_switch_id]
                mirrored_switch_ports[mirror_switch_dpid].append(actual_port_number)
        return dict(mirrored_switch_ports)
    
    mirrored_ports_json = create_mirrored_ports_json(solutions, id_to_dpid,
            port_ids_to_port_numbers)
    flow_path_json      = create_path_json(flow_def)
    port_number_json    = create_port_numbers_json(flow_def, port_ids_to_port_numbers, id_to_dpid)
    json_dict = { "flowRoute"       : flow_path_json
                , "portNumbers"     : port_number_json
                , "tagValue"        : tag_value
                , "mirroredPorts"   : mirrored_ports_json
                }
    return json.dumps(json_dict)

def request_flow_mirroring(flow_def, switches, solution_def, id_to_dpid, tag_value):
    json_body = create_add_flow_mirroring_rules_request_json(flow_def, switches, solution_def, 
            id_to_dpid, tag_value)
    rest_endpoint = url.urljoin(cfg.onos_url.geturl(), "port-mirroring/v1/add-mirrored-flow")
    port_mirroring_request = req.post(rest_endpoint, data=json_body, auth=cfg.ONOS_API_CREDENTIALS)
    if port_mirroring_request.status_code != 200:
        pp.pprint(port_mirroring_request.text)
        raise ValueError("add-mirrored-flow request failed with code %d %s" % 
                (port_mirroring_request.status_code, port_mirroring_request.reason))
    else:
        print("Successfully added mirrored flow")
        response = json.loads(port_mirroring_request.text)
        return response["routeId"]

def request_port_mirroring( flow_def
                          , switches
                          , solution_def
                          , id_to_dpid
                          , tag_value
                          , port_ids_to_port_numbers):
    json_body = create_add_port_mirroring_rules_request_json(flow_def, switches, solution_def, 
            id_to_dpid, tag_value, port_ids_to_port_numbers)   
    rest_endpoint = url.urljoin(cfg.onos_url.geturl(), "port-mirroring/v1/add-mirrored-ports")
    port_mirroring_request = req.post(rest_endpoint, data=json_body, auth=cfg.ONOS_API_CREDENTIALS)
    if port_mirroring_request.status_code != 200:
        pp.pprint(port_mirroring_request.text)
        raise ValueError("add-mirrored-ports request failed with code %d %s" %
                (port_mirroring_request.status_code, port_mirroring_request.reason))
    else:
        print("Successfully added mirrored ports")
        response = json.loads(port_mirroring_request.text)
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

def remove_port_mirroring_flows(flow_tokens):
    for flow_token in flow_tokens.values():
        remove_port_mirroring_rules(flow_token)

def map_port_ids_to_nw_ports(mirroring_ports, id_to_dpid):
    # switch_id -> port_id -> port_number
    dpid_port_map = defaultdict(dict)
    for source_id, destination_id_to_port_number in mirroring_ports.port_map.items():
        for destination_id, port_number in destination_id_to_port_number.items():
            source_dpid         = id_to_dpid[source_id]
            destination_dpid    = id_to_dpid[destination_id]
            source_port, destination_port = topo_mapper.get_ports_that_connect(source_dpid, 
                    destination_dpid)
            dpid_port_map[source_id][port_number] = source_port
    
    return dpid_port_map

def add_flow_mirroring_flows(topology, flows, switches, solutions):
    flow_ids_to_add = flows.keys()
    id_to_dpid = topo_mapper.get_and_validate_onos_topo(topology)
    flow_tokens = {}
    for flow_id in flow_ids_to_add:
        flow_tokens[flow_id] = request_flow_mirroring(flows[flow_id], switches, 
                solutions[flow_id], id_to_dpid, flow_id)
    return flow_tokens

def add_port_mirroring_flows(topology, flows, switches, solutions, mirroring_ports):
    flow_ids_to_add = flows.keys()
    id_to_dpid = topo_mapper.get_and_validate_onos_topo(topology)
    port_ids_to_port_numbers = map_port_ids_to_nw_ports(mirroring_ports, id_to_dpid)
    flow_tokens = {}

    verify_that_all_flows_are_mirrored(flows, switches, solutions, port_ids_to_port_numbers,
            id_to_dpid)

    for flow_id in flow_ids_to_add:
        flow_tokens[flow_id] = request_port_mirroring(flows[flow_id], switches, solutions,
                id_to_dpid, flow_id, port_ids_to_port_numbers)
    return flow_tokens
