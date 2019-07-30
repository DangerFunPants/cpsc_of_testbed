
import pathlib          as path
import subprocess       as subprocess
import json             as json

import port_mirroring.onos_rest_helpers            as onos_rest_helpers

class FlowDefinition:
    def __init__(self, flow_id, traffic_rate, path):
        self._flow_id           = flow_id
        self._traffic_rate      = traffic_rate
        self._path              = path

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def traffic_rate(self):
        return self._traffic_rate

    @property
    def path(self):
        return self._path

    @staticmethod
    def serialize(flows):
        def to_undelimited_list(python_list):
            s = ""
            for elem in python_list[:-1]:
                s += "%d " % elem
            s += "%d" % python_list[-1]
            return s
                
        s = ""
        for flow in flows.values():
            s += "%d %f %s\n" % (flow.flow_id, flow.traffic_rate, to_undelimited_list(flow.path))
        return s

    @staticmethod
    def deserialize(text):
        flows = {}
        for line in text.splitlines():
            tokens = line.split(" ")
            [flow_id, traffic_rate], path = tokens[:2], tokens[2:]
            flow_id = int(flow_id)
            traffic_rate = float(traffic_rate)
            path = [int(node_id) for node_id in path]
            flow_def = FlowDefinition(flow_id, traffic_rate, path)
            flows[flow_id] = flow_def
        return flows

    def __str__(self):
        return ("FlowDefinition {flow_id: %d, traffic_rate: %f, path: %s}" %
                    (self.flow_id, self.traffic_rate, self.path))

class SwitchDefinition:
    def __init__(self, switch_id, resident_flows):
        self._switch_id         = switch_id
        self._resident_flows    = resident_flows

    @property
    def switch_id(self):
        return self._switch_id

    @property
    def resident_flows(self):
        return self._resident_flows

    @staticmethod
    def serialize(switches):
        def to_undelimited_list(python_list):
            s = ""
            for elem in python_list[:-1]:
                s += "%d " % elem
            s += "%d" % python_list[-1]
            return s

        s = ""
        for switch in switches.values():
            if len(switch.resident_flows) > 0:
                s += "%d %s\n" % (switch.switch_id, to_undelimited_list(switch.resident_flows))
            else:
                s += "%d\n" % (switch.switch_id)
        return s

    @staticmethod
    def deserialize(text):
        switches = {}
        for line in text.splitlines():
            tokens = line.split(" ")
            [[switch_id], resident_flows] = tokens[:1], tokens[1:]
            switch_id = int(switch_id)
            resident_flows = [int(flow_id) for flow_id in resident_flows]
            switch_def = SwitchDefinition(switch_id, resident_flows)
            switches[switch_id] = switch_def
        return switches

    def __str__(self):
        return ("SwitchDefinition {switch_id: %d, resident_flows: %s}" % 
                    (self.switch_id, self.resident_flows))

class SolutionDefinition:
    def __init__(self, flow_id, mirror_switch_id, objective_value):
        self._flow_id           = flow_id
        self._mirror_switch_id  = mirror_switch_id
        self._objective_value   = objective_value

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def mirror_switch_id(self):
        return self._mirror_switch_id

    @property
    def objective_value(self):
        return self._objective_value    

    @staticmethod
    def serialize(solutions):
        s = ""
        objective_value = None
        for solution in solutions.values():
            objective_value = solution.objective_value
            s += "%d %d\n" % (solution.flow_id, solution.mirror_switch_id)
        s += "%f" % objective_value
        return s

    @staticmethod
    def deserialize(text):
        solutions = {}
        lines = text.splitlines()
        objective_value = float(lines[-1])
        for line in lines[:-1]:
            [flow_id, mirror_switch_id] = line.split(" ")
            flow_id = int(flow_id)
            mirror_switch_id = int(mirror_switch_id)
            solution_def = SolutionDefinition(flow_id, mirror_switch_id, objective_value)
            solutions[flow_id] = solution_def
        return solutions

    def __str__(self):
        return ("SolutionDefinition {flow_id: %d, mirror_switch_id: %d}" %
                    (self.flow_id, self.mirror_switch_id))

class FlowMirroringTrial:
    SOLVER_PATH         = path.Path("/home/cpsc-net-user/repos/flow-mirroring-scheme/")
    TOPOLOGY_FILE       = SOLVER_PATH.joinpath("network/temp-topo.txt")

    def __init__( self
                , topology
                , flows
                , switches
                , approx_solutions
                , optimal_solutions
                , duration
                , name):
        self._topology              = topology
        self._flows                 = flows
        self._switches              = switches
        self._approx_solutions      = approx_solutions
        self._optimal_solutions     = optimal_solutions
        self._duration              = duration
        self._name                  = name
        self._solutions             = approx_solutions
        self._solution_type         = "approx"

    @property
    def topology(self):
        return self._topology

    @property
    def flows(self):
        return self._flows

    @property
    def switches(self):
        return self._switches

    @property
    def approx_solutions(self):
        return self._approx_solutions

    @property
    def optimal_solutions(self):
        return self._optimal_solutions

    @property
    def solutions(self):
        return self._solutions

    @property
    def duration(self):
        return self._duration

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def solution_type(self):
        return self._solution_type

    @solution_type.setter
    def solution_type(self, new_solution_type):
        self._solution_type = new_solution_type

    def add_flows(self):
        flow_tokens = onos_rest_helpers.add_flow_mirroring_flows(self.topology, self.flows, self.switches,
                self.solutions)
        return flow_tokens

    def set_solution_type(self, type_name):
        lower_type_name = type_name.lower()
        if lower_type_name == "optimal":
            self._solutions = self._optimal_solutions
        elif lower_type_name == "approx":
            self_solutions = self._approx_solutions
        else:
            raise ValueError("Do not recognize solution type %s" % type_name)
        self.solution_type = lower_type_name

    def get_solution_types(self):
        solution_types = [ "approx"
                         , "optimal"
                         ]
        return solution_types

    @staticmethod
    def create_trial(topology, minimum_flow_rate, maximum_flow_rate, num_flows, duration, name):
        FlowMirroringTrial.invoke_solver_with_params(topology, minimum_flow_rate,
                maximum_flow_rate, num_flows)
        flows_file              = FlowMirroringTrial.SOLVER_PATH.joinpath("network/flows")
        switches_file           = FlowMirroringTrial.SOLVER_PATH.joinpath("network/switches")
        approx_solutions_file   = FlowMirroringTrial.SOLVER_PATH.joinpath("solutions/approx")
        optimal_solutions_file  = FlowMirroringTrial.SOLVER_PATH.joinpath("solutions/opt")

        flows               = FlowDefinition.deserialize(flows_file.read_text())
        switches            = SwitchDefinition.deserialize(switches_file.read_text()) 
        approx_solutions    = SolutionDefinition.deserialize(approx_solutions_file.read_text())
        optimal_solutions   = SolutionDefinition.deserialize(optimal_solutions_file.read_text())

        trial = FlowMirroringTrial(topology, flows, switches, approx_solutions, 
                optimal_solutions, duration, name)
        return trial

    @staticmethod
    def invoke_solver_with_params(topology, minimum_flow_rate, maximum_flow_rate, num_flows):
        def create_solver_cmd(topology, minimum_flow_rate, maximum_flow_rate, num_flows):
            FlowMirroringTrial.TOPOLOGY_FILE.write_text(topology)
            base_cmd = FlowMirroringTrial.SOLVER_PATH.joinpath("invoke_solver.sh")
            args = [ FlowMirroringTrial.TOPOLOGY_FILE.name
                   , str(num_flows)
                   , str(minimum_flow_rate)
                   , str(maximum_flow_rate)
                   ]
            cmd = [str(base_cmd)] + args
            return cmd
        
        cmd = create_solver_cmd(topology, minimum_flow_rate, maximum_flow_rate, num_flows)
        subprocess.run(cmd)

    def verify_trial(self):
        for flow_id, flow in self.flows.items():
            if flow_id not in self.approx_solutions:
                return False
            if flow_id not in self.optimal_solutions:
                return False
        return True

    def build_results_files(self, utilization_results):
        results_files = { "utilization-results.txt" : json.dumps(utilization_results)
                        , "topo"                    : self.topology
                        , "flows"                   : FlowDefinition.serialize(self.flows)
                        , "switches"                : SwitchDefinition.serialize(self.switches)
                        , "solutions"               : SolutionDefinition.serialize(self.solutions)
                        }
        return results_files

    def __str__(self):
        s = "Flows:\n"
        for flow in self._flows.values():
            s += "\t%s\n" % str(flow)
        s += "\nSolutions:\n"
        for solution in self._approx_solutions.values():
            s += "\t%s\n" % str(solution)
        return s

