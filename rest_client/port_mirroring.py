
import pathlib              as path
import pprint               as pp
import json                 as json
import requests             as req

from collections import namedtuple

INPUT_FILE_DIR = path.Path("./port-mirroring-inputs")
ONOS_API_CREDENTIALS = ("onos", "rocks")
DPID_TO_ID = { "of:00039cdc718ae5c0": 6
             , "of:00049cdc718ae5c0": 7
             , "of:00039cdc718a17c0": 1
             , "of:00049cdc718a17c0": 2
             , "of:00059cdc718a17c0": 11
             , "of:00039cdc718ab520": 3
             , "of:00049cdc718ab520": 4
             , "of:00059cdc718ab520": 10
             , "of:000400fd457cab40": 5
             , "of:000500fd457cab40": 9
             , "of:00069cdc718ae5c0": 8
             , "of:000700fd457cab40": "C"
             }

ID_TO_DPID = {v: k for k, v in DPID_TO_ID.items()}

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

def create_add_mirroring_rules_request_json(flow_def, switches, solution_def):
    def create_path_json(flow_def):
        path_json_dict = {"nodes": [ID_TO_DPID[node_id] for node_id in flow_def.path]}
        return path_json_dict

    json_dict = { "mirrorSwitch"        : ID_TO_DPID[solution_def.mirror_switch_id]
                , "tagValue"            : 0
                , "flowRoute"           : create_path_json(flow_def)
                }
    return json.dumps(json_dict)

def create_all_mirroring_rules_requests(flows, switches, solutions):
    requests_list = []
    for flow_id in flows.keys():
        flow_json = create_add_mirroring_rules_request_json(flows[flow_id], switches, 
                solutions[flow_id])
        requests_list.append(flow_json)

    return requests_list

def request_port_mirroring(flow_def, switches, solution_def):
    json_body = create_add_mirroring_rules_request_json(flow_def, switches, solution_def)
    rest_endpoint = "http://127.0.0.1:8181/onos/port-mirroring/v1/add-mirrored-flow"
    port_mirroring_request = req.post(rest_endpoint, data=json_body, auth=ONOS_API_CREDENTIALS)
    if port_mirroring_request.status_code != 200:
        pp.pprint(port_mirroring_request.text)
        raise ValueError("add-mirrored-flow request failed with code %d and reason %s" % 
                (port_mirroring_request.status_code, port_mirroring_request.reason))
    else:
        print("Successfully added mirrored flow")
        response = json.loads(port_mirroring_request.text)
        pp.pprint(response)

def add_port_mirroring_routes():
    flow_file_path          = INPUT_FILE_DIR.joinpath("flows")
    switch_file_path        = INPUT_FILE_DIR.joinpath("switches")
    solution_file_path      = INPUT_FILE_DIR.joinpath("approx")
    
    flows           = parse_flows_from_file(flow_file_path)
    switches        = parse_switches_from_file(switch_file_path)
    solutions       = parse_solutions_from_file(solution_file_path)

    pp.pprint(flows)
    pp.pprint(switches)
    pp.pprint(solutions)

    flow_ids_to_add = [1]
    # for flow_id in flows.keys():
    for flow_id in flow_ids_to_add:
        request_port_mirroring(flows[flow_id], switches, solutions[flow_id])

def main():
    add_port_mirroring_routes()

if __name__ == "__main__":
    main()
