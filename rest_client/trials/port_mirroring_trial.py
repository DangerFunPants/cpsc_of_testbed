
import pathlib              as path
import pprint               as pp
import subprocess           as subprocess
import json                 as json

import port_mirroring.onos_rest_helpers     as onos_rest_helpers
import nw_control.topo_mapper               as topo_mapper

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
            path = [(int(path_str[idx]), int(path_str[idx+1])) 
                    for idx in range(0, len(path_str)-1, 2)]
            path.append((int(path_str[-1]), 0))
            flow_id = int(flow_id)
            traffic_rate = float(traffic_rate)
            flows[flow_id] = PortMirroringFlow(flow_id, traffic_rate, path)
        return flows

    def __str__(self):
        return ("PortMirroringFlow {flow_id: %d, traffic_rate: %f, path: %s}" %
                (self.flow_id, self.traffic_rate, list(zip(self.path, self.ports))))

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

    def get_port(self, port_id):
        for port in self.ports:
            if port.port_id == port_id:
                return port
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
                (self.switch_id, str([str(port) for port in self.ports])))
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
        for solution_id, solution_list in solutions.items():
            for solution in solution_list:
                objective = solution.objective_value
                s += "%d %d\n" % (solution.mirror_switch_id, solution.mirror_switch_port)
        s += "%f" % objective
        return s

    @staticmethod
    def deserialize(text):
        solutions = defaultdict(list)
        lines = text.splitlines()
        objective_value = float(lines[-1])
        for line in lines[:-1]:
            [switch_id, port_id]            = line.split(" ")
            mirror_switch_id                = int(switch_id)
            mirror_port_id                  = int(port_id)
            solutions[mirror_switch_id].append(PortMirroringSolution(mirror_switch_id,
                    mirror_port_id, objective_value))
        return solutions

    def __str__(self):
        s = ("PortMirroringSolution { mirror_switch_id: %s, mirror_switch_port: %s, objective_value: %f" % (self.mirror_switch_id, self.mirror_switch_port, self.objective_value))
        return s

class RndPortMirroringSolution:
    def __init__( self
                , mirror_switch_id
                , mirror_switch_port
                , objective_value
                , coverage):
        self._mirror_switch_id      = mirror_switch_id
        self._mirror_switch_port    = mirror_switch_port
        self._objective_value       = objective_value
        self._coverage              = coverage

    @property
    def mirror_switch_id(self):
        return self._mirror_switch_id

    @property
    def mirror_switch_port(self):
        return self._mirror_switch_port

    @property
    def objective_value(self):
        return self._objective_value

    @property
    def coverage(self):
        return self._coverage

    @staticmethod
    def serialize(rnd_solutions):
        s = ""
        objective       = None
        coverage        = None
        for solution_id, solution_list in rnd_solutions.items():
            for solution in solutions_list:
                objective   = solution.objective_value
                coverage    = solution.coverage
                s += "%d %d\n" % (solution.mirror_switch_id, solution.mirror_switch_port)
        s += "%f\n" % objective
        s += "%f\n" % coverage
        return s

    @staticmethod
    def deserialize(text):
        solutions = defaultdict(list)
        lines = text.splitlines()
        objective_value = float(lines[-2])
        coverage        = float(lines[-1])
        for line in lines[:-2]:
            [switch_id, port_id]        = line.split(" ")
            mirror_switch_id            = int(switch_id)
            mirror_port_id              = int(port_id)
            solutions[mirror_switch_id].append(RndPortMirroringSolution(mirror_switch_id,
                mirror_port_id, objective_value, coverage))
        return solutions

    def __str__(self):
        s = ("RndPortMirroringSolution { mirror_switch_id: %s, mirror_switch_port: %s, objective_value: %s, coverage: %s" %
                (self.mirror_switch_id, self.mirror_switch_port, 
                    self.objective_value, self.coverage))
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
        self._solution_types        = [ "det"
                                      , "df"
                                      , "greedy"
                                      , "optimal"
                                      , "rnd"
                                      ]

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

    @property
    def solution_types(self):
        return self._solution_types

    @solution_types.setter
    def solution_types(self, new_solution_types):
        self._solution_types = new_solution_types

    def get_solution_of_type(self, solution_type):
        if solution_type == "df":
            return self._df_solutions
        elif solution_type == "optimal":
            return self._optimal_solutions
        elif solution_type == "det":
            return self._det_solutions
        elif solution_type == "greedy":
            return self._greedy_solutions
        elif solution_type == "rnd":
            return self._rnd_solutions

    def verify_trial_state(self):
        flows = self.flows
        switches = self.switches
        for solution_type in self.get_solution_types():
            mirrored_flows = set()
            solution = self.get_solution_of_type(solution_type) 
            for _, solution_list in solution.items():
                for solution in solution_list:
                    switch_id       = solution.mirror_switch_id
                    port_id         = solution.mirror_switch_port
                    port            = switches[switch_id].get_port(port_id)
                    print(port.flow_list)
                    for flow_id in port.flow_list:
                        mirrored_flows.add(flow_id)
        return len(mirrored_flows) == len(flows)

    def add_flows(self):
        flow_tokens = onos_rest_helpers.add_port_mirroring_flows(self.topology, self.flows, self.switches,
                self.solutions, self.mirroring_ports)
        return flow_tokens

    @property
    def mirroring_ports(self):
        return self._mirroring_ports

    def get_solution_types(self):
        return self.solution_types

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
        rnd_solutions_file      = PortMirroringTrial.SOLVER_PATH.joinpath("solutions/rnd")

        flows               = PortMirroringFlow.deserialize(flows_file.read_text())
        switches            = PortMirroringSwitch.deserialize(switches_file.read_text())
        mirroring_ports     = PortMirroringPorts.deserialize(ports_file.read_text())
        det_solutions       = PortMirroringSolution.deserialize(det_solutions_file.read_text())
        df_solutions        = PortMirroringSolution.deserialize(df_solutions_file.read_text())
        greedy_solutions    = PortMirroringSolution.deserialize(greedy_solutions_file.read_text())
        optimal_solutions   = PortMirroringSolution.deserialize(optimal_solutions_file.read_text())
        rnd_solutions       = RndPortMirroringSolution.deserialize(rnd_solutions_file.read_text())

        trial = PortMirroringTrial(topology, flows, switches, det_solutions, df_solutions,
                    greedy_solutions, optimal_solutions, rnd_solutions, duration, name,
                    mirroring_ports)
        return trial

    @staticmethod
    def from_repository_files(results_repository, schema_variables, duration, name):
        files = [ "flows"
                , "switches"
                , "solutions"
                , "ports"
                , "topo"
                ]
        results             = results_repository.read_trial_results(schema_variables, files)
        flows               = PortMirroringFlow.deserialize(results["flows"])
        solutions           = PortMirroringSolution.deserialize(results["solutions"])
        switches            = PortMirroringSwitch.deserialize(results["switches"])
        mirroring_ports     = PortMirroringPorts.deserialize(results["ports"])
        topology            = results["topo"]

        det_solutions       = None 
        df_solutions        = None
        greedy_solutions    = None
        optimal_solutions   = None
        rnd_solutions       = None
        solution_type = schema_variables["solution-type"]
        if solution_type == "det":
            det_solutions = solutions
        elif solution_type == "df":
            df_solutions = solutions
        elif solution_type == "greedy":
            greedy_solutions = solutions
        elif solution_type == "optimal":
            optimal_solutions = solutions
        elif solution_type == "rnd":
            rnd_solutions = solutions
        else:
            raise ValueError("Unrecognized solution type %s" % solution_type)

        trial = PortMirroringTrial(topology, flows, switches, det_solutions, df_solutions,
                greedy_solutions, optimal_solutions, rnd_solutions, duration, name,
                mirroring_ports)
        trial.solution_types = [solution_type]
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

    @staticmethod
    def map_to_physical_network(trial):
        id_to_dpid = topo_mapper.get_and_validate_onos_topo(trial.topology)
        port_ids_to_port_numbers = onos_rest_helpers.map_port_ids_to_nw_ports(
                trial.mirroring_ports, id_to_dpid)

        new_flows = {}
        for flow_id, flow in trial.flows.items():
            new_path = [id_to_dpid[node] for node in flow.path]
            new_ports = [port_ids_to_port_numbers[switch_id][port] 
                    for switch_id, port in zip(flow.path[:-1], flow.ports[:-1])]
            zipped_path = list(zip(new_path, new_ports))
            
            last_hop_switch_dpid    = id_to_dpid[flow.path[-1]]
            last_hop_egress_port    = topo_mapper.get_host_port(last_hop_switch_dpid)
            zipped_path.append((last_hop_switch_dpid, last_hop_egress_port))
            new_flow = PortMirroringFlow(flow_id, flow.traffic_rate, zipped_path)
            new_flows[flow_id] = new_flow

        new_solutions = defaultdict(list)
        for switch_id, solution_list in trial.solutions.items():
            for solution in solution_list:
                new_mirror_switch_id = id_to_dpid[solution.mirror_switch_id]
                new_mirror_switch_port = port_ids_to_port_numbers[solution.mirror_switch_id][solution.mirror_switch_port]
                new_solution = PortMirroringSolution(new_mirror_switch_id, new_mirror_switch_port,
                        solution.objective_value)
                new_solutions[switch_id].append(new_solution)

        solutions = {}
        solutions[trial.solution_type] = new_solutions
        det_solutions = solutions.get("det", None)
        df_solutions = solutions.get("df", None)
        greedy_solutions = solutions.get("greedy", None)
        optimal_solutions = solutions.get("optimal", None)
        rnd_solutions = solutions.get("rnd", None)
        new_trial = PortMirroringTrial(trial.topology, new_flows, trial.switches, det_solutions,
                df_solutions, greedy_solutions, optimal_solutions, rnd_solutions,
                trial.duration, trial.name, trial.mirroring_ports)
        print("solution_type %s" % trial.solution_type)
        pp.pprint(solutions)
        new_trial.set_solution_type(trial.solution_type)
        return new_trial

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
            s += "\t%s\n" % str([str(s) for s in solution])
        return s

