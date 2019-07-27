
import pathlib              as path
import pprint               as pp
import subprocess           as subprocess
import json                 as json

import port_mirroring.onos_rest_helpers     as onos_rest_helpers

from collections                import defaultdict

class PortMirroringFlow:
    def __init__(self, flow_id, traffic_rate, path):
        self._flow_id       = flow_id
        self._traffic_rate  = traffic_rate
        self._path          = path

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def traffic_rate(self):
        return self._traffic_rate

    @property
    def path(self):
        return [t[0] for t in self._path]

    @property
    def ports(self):
        return [t[1] for t in self._path]

    @staticmethod
    def serialize(flows):
        def path_to_str(path):
            s = ""
            for node_id, port_id in path[:-1]:
                s += "%d %d " % (node_id, port_id)
            if len(path) > 0:
                s += "%d %d" % (path[-1][0], path[-1][1])
            return s

        s = ""
        for flow_id, flow in flows.items():
            s += "%d %f %s\n" % (flow.flow_id, flow.traffic_rate, path_to_str(list(zip(flow.path, flow.ports))))
        return s

    @staticmethod
    def deserialize(text):
        flows = {}
        for line in text.splitlines():
            tokens = line.split(" ")
            [flow_id, traffic_rate], path_str = tokens[:2], tokens[2:]
            path = [(path_str[idx], path_str[idx+1]) for idx in range(0, len(path_str), 2)]
            flow_id = int(flow_id)
            traffic_rate = float(traffic_rate)
            path = [(int(node_id), int(switch_id)) for node_id, switch_id in path]
            flows[flow_id] = PortMirroringFlow(flow_id, traffic_rate, path)
        return flows

    def __str__(self):
        return ("PortMirroringFlow {flow_id: %d, traffic_rate: %f, path: %s}" %
                (self.flow_id, self.traffic_rate, self.path))

class SwitchPort:
    def __init__(self, port_id, flow_rate, flow_list):
        self._port_id       = port_id
        self._flow_rate     = flow_rate
        self._flow_list     = flow_list

    @property
    def port_id(self):
        return self._port_id

    @property
    def flow_rate(self):
        return self._flow_rate

    @property
    def flow_list(self):
        return self._flow_list

    def __str__(self):
        s = ("SwitchPort { port_id: %d, port_rate: %f, flow_list: %s }" %
                (self.port_id, self.flow_rate, str(self.flow_list)))
        return s

class PortMirroringSwitch:
    def __init__( self
                , switch_id
                , ports):
        self._switch_id     = switch_id
        self._ports         = ports

    @property
    def switch_id(self):
        return self._switch_id

    @property
    def ports(self):
        return self._ports

    def rate_for_port(self, port_id):
        for port in self.ports:
            if port.port_id == port_id:
                return port.flow_rate
        raise ValueError("Switch %d does not have port with ID %d" % (self.switch_id, port_id))

    @staticmethod
    def serialize(switches):
        def flow_list_to_str(flow_list):
            s = ""
            for flow_id in flow_list[:-1]:
                s += "%d " % flow_id
            if len(flow_list) > 0:
                s += "%d" % flow_list[-1]
            return s

        s = ""
        for switch_id, switch in switches.items():
            for port in switch.ports:
                s += "%d %d %f %s\n" % (switch.switch_id, port.port_id, port.flow_rate,
                        flow_list_to_str(port.flow_list))
        return s
            
    @staticmethod
    def deserialize(text):
        ports       = defaultdict(list)
        for line in text.splitlines():
            tokens = line.split(" ")
            [switch_id, port_id, port_rate], flow_list = tokens[:3], tokens[3:]
            switch_id   = int(switch_id)
            port_id     = int(port_id)
            port_rate   = float(port_rate) 
            flow_list   = [int(flow) for flow in flow_list if flow != ""]
            ports[switch_id].append(SwitchPort(port_id, port_rate, flow_list))

        switches = {}
        for switch_id, ports in ports.items():
            switches[switch_id] = PortMirroringSwitch(switch_id, ports)
        return switches

    def __str__(self):
        s = ("PortMirroringSwitch { switch_id: %d, ports: %s" %
                (self.switch_id, str(self.ports)))
        return s

class PortMirroringSolution:
    def __init__(self, mirror_switch_id, mirror_switch_port, objective_value):
        self._mirror_switch_id      = mirror_switch_id
        self._mirror_switch_port    = mirror_switch_port
        self._objective_value       = objective_value

    @property
    def mirror_switch_id(self):
        return self._mirror_switch_id

    @property
    def mirror_switch_port(self):
        return self._mirror_switch_port

    @property
    def objective_value(self):
        return self._objective_value

    @staticmethod
    def serialize(solutions):
        s = ""
        objective = None
        for solution_id, solution in solutions.items():
            objective = solution.objective_value
            s += "%d %d\n" % (solution.mirror_switch_id, solution.mirror_switch_port)
        s += "%f" % objective
        return s

    @staticmethod
    def deserialize(text):
        solutions = {}
        lines = text.splitlines()
        objective_value = float(lines[-1])
        for line in lines[:-1]:
            [switch_id, port_id]            = line.split(" ")
            mirror_switch_id                = int(switch_id)
            mirror_port_id                  = int(port_id)
            solutions[mirror_switch_id]     = PortMirroringSolution(mirror_switch_id,
                    mirror_port_id, objective_value)
        return solutions

    def __str__(self):
        s = ("PortMirroringSolution { mirror_switch_id: %d, mirror_switch_port: %d, objective_value: %f" % (self.mirror_switch_id, self.mirror_switch_port, self.objective_value))
        return s

class PortMirroringPorts:
    def __init__(self, port_map):
        self._port_map = port_map

    def get_port_connecting(self, source_switch, destination_switch):
        return self._port_map[source_switch][destination_switch]

    @property
    def port_map(self):
        return self._port_map

    @staticmethod
    def serialize(port_mirroring_ports):
        return pp.pformat(port_mirroring_ports._port_map)

    @staticmethod
    def deserialize(text):
        port_map = eval(text)
        return PortMirroringPorts(port_map)

class PortMirroringTrial:
    SOLVER_PATH     = path.Path("/home/cpsc-net-user/repos/port-mirroring-scheme/")
    TOPOLOGY_FILE   = SOLVER_PATH.joinpath("network/temp-topo.txt")

    def __init__( self
                , topology
                , flows
                , switches
                , det_solutions
                , df_solutions
                , greedy_solutions
                , optimal_solutions
                , rnd_solutions
                , duration
                , name
                , mirroring_ports):
        self._topology              = topology
        self._flows                 = flows
        self._switches              = switches
        self._det_solutions         = det_solutions
        self._df_solutions          = df_solutions
        self._greedy_solutions      = greedy_solutions
        self._optimal_solutions     = optimal_solutions
        self._rnd_solutions         = rnd_solutions
        self._duration              = duration
        self._name                  = name
        self._solutions             = optimal_solutions
        self._solution_type         = "optimal"
        self._mirroring_ports       = mirroring_ports
    
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
    def det_solutions(self):
        return self._det_solutions

    @property
    def df_solutions(self):
        return self._df_solutions

    @property
    def greedy_solutions(self):
        return self._greedy_solutions

    @property
    def optimal_solutions(self):
        return self._optimal_solutions

    @property
    def rnd_solutions(self):
        return self._rnd_solutions

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
    def name(self, new_name):
        self._name = new_name

    @property
    def solution_type(self):
        return self._solution_type

    @solution_type.setter
    def solution_type(self, new_solution_type):
        self._solution_type = new_solution_type

    def add_flows(self):
        flow_tokens = onos_rest_helpers.add_port_mirroring_flows(self.topology, self.flows, self.switches,
                self.solutions, self.mirroring_ports)
        return flow_tokens

    @property
    def mirroring_ports(self):
        return self._mirroring_ports

    def get_solution_types(self):
        solution_types = [ "det"
                         , "df"
                         , "greedy"
                         , "optimal"
                         ]
        return solution_types

    def set_solution_type(self, type_name):
        lower_type_name = type_name.lower()
        if lower_type_name == "det":
            self._solutions = self._det_solutions
        elif lower_type_name == "df":
            self._solutions = self._df_solutions
        elif lower_type_name == "greedy":
            self._solutions = self._greedy_solutions
        elif lower_type_name == "optimal":
            self._solutions = self._optimal_solutions
        elif lower_type_name == "rnd":
            self._solutions = self._rnd_solutions
        else:
            raise ValueError("Do not recognize solution type %s" % lower_type_name)
        self._solution_type = lower_type_name

    @staticmethod
    def create_trial(topology, minimum_flow_rate, maximum_flow_rate, num_flows, duration, name):
        PortMirroringTrial.invoke_solver_with_params(topology, minimum_flow_rate,
                maximum_flow_rate, num_flows)
        flows_file              = PortMirroringTrial.SOLVER_PATH.joinpath("network/flows")
        switches_file           = PortMirroringTrial.SOLVER_PATH.joinpath("network/switches")
        ports_file              = PortMirroringTrial.SOLVER_PATH.joinpath("network/ports")
        det_solutions_file      = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/det")
        df_solutions_file       = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/df")
        greedy_solutions_file   = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/greedy_port")
        optimal_solutions_file  = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/opt")
        # rnd_solutions_file      = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/rnd")

        flows               = PortMirroringFlow.deserialize(flows_file.read_text())
        switches            = PortMirroringSwitch.deserialize(switches_file.read_text())
        mirroring_ports     = PortMirroringPorts.deserialize(ports_file.read_text())
        det_solutions       = PortMirroringSolution.deserialize(det_solutions_file.read_text())
        df_solutions        = PortMirroringSolution.deserialize(df_solutions_file.read_text())
        greedy_solutions    = PortMirroringSolution.deserialize(greedy_solutions_file.read_text())
        optimal_solutions   = PortMirroringSolution.deserialize(optimal_solutions_file.read_text())
        # rnd_solutions       = PortMirroringSolution.deserialize(rnd_solutions_file.read_text())
        rnd_solutions       = None

        trial = PortMirroringTrial(topology, flows, switches, det_solutions, df_solutions,
                    greedy_solutions, optimal_solutions, rnd_solutions, duration, name,
                    mirroring_ports)
        return trial

    @staticmethod
    def invoke_solver_with_params(topology, minimum_flow_rate, maximum_flow_rate, num_flows):
        def create_solver_cmd(topology, minimum_flow_rate, maximum_flow_rate, num_flows):
            PortMirroringTrial.TOPOLOGY_FILE.write_text(topology)
            base_cmd = PortMirroringTrial.SOLVER_PATH.joinpath("invoke_solver.sh")
            args = [ PortMirroringTrial.TOPOLOGY_FILE.name
                   , str(num_flows)
                   , str(minimum_flow_rate)
                   , str(maximum_flow_rate)
                   ]
            cmd = [str(base_cmd)] + args
            return cmd
        
        cmd = create_solver_cmd(topology, minimum_flow_rate, maximum_flow_rate, num_flows)
        subprocess.run(cmd)

    def build_results_files(self, utilization_results):
        utilization_text    = json.dumps(utilization_results)
        flow_text           = PortMirroringFlow.serialize(self.flows)
        switch_text         = PortMirroringSwitch.serialize(self.switches)
        solution_text       = PortMirroringSolution.serialize(self.solutions)
        ports_text          = PortMirroringPorts.serialize(self.mirroring_ports)

        results_files = { "utilization-results.txt"     : utilization_text
                        , "topo"                        : self.topology
                        , "flows"                       : flow_text
                        , "switches"                    : switch_text
                        , "solutions"                   : solution_text
                        , "ports"                       : ports_text
                        }
        return results_files

    def __str__(self):
        s = "Flows:\n"
        for flow in self._flows.values():
            s += "\t%s\n" % str(flow)
        s += "\nSolutions:\n"
        for solution in self.solutions.values():
            s += "\t%s\n" % str(solution)
        return s

