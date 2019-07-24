
from collections import namedtuple

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

