
import pathlib          as path
import subprocess       as subprocess

# How do I want this API to work? 
#   * Load a series of trials
#       * How to specify trials?
#       * Build a bunch of trial objects then aggregate them in a trial_provider
#         that can be consumed by the test runner.
#   * Query paramaters necessary to run the trials
#       * topology
#       * flows file
#       * switch file
#       * solution file
#
# How to build trial objects?
#   * initialize Trial object with parameters then invoke solvers.
#       * Need to run solvers in correct environment (python2.7 w/gurobipy)
#       * Could wrap solver in shell script then invoke shell script to 
#         generate outputs.

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
        s = ""
        for flow in flows.values():
            s += "%d %f %s\n" % (flow.flow_id, flow.traffic_rate, flow.path)
        return s

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
        s = ""
        for switch in switches.values():
            s += "%d %s\n" % (switch.switch_id, switch.resident_flows)
        return s

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
    def duration(self):
        return self._duration

    @property
    def name(self):
        return self._name

    @staticmethod
    def create_trial(topology, minimum_flow_rate, maximum_flow_rate, num_flows, duration, name):
        FlowMirroringTrial.invoke_solver_with_params(topology, minimum_flow_rate,
                maximum_flow_rate, num_flows)
        flows_file              = FlowMirroringTrial.SOLVER_PATH.joinpath("network/flows")
        switches_file           = FlowMirroringTrial.SOLVER_PATH.joinpath("network/switches")
        approx_solutions_file   = FlowMirroringTrial.SOLVER_PATH.joinpath("solutions/approx")
        optimal_solutions_file  = FlowMirroringTrial.SOLVER_PATH.joinpath("solutions/opt")

        flows               = FlowMirroringTrial.parse_flows_from_file(flows_file)
        switches            = FlowMirroringTrial.parse_switches_from_file(switches_file)
        approx_solutions    = FlowMirroringTrial.parse_solutions_from_file(approx_solutions_file)
        optimal_solutions   = FlowMirroringTrial.parse_solutions_from_file(optimal_solutions_file)

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

    @staticmethod
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
            
    @staticmethod
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

    @staticmethod
    def parse_solutions_from_file(file_path):
        with file_path.open("r") as fd:
            lines = fd.readlines()
        solutions = {}
        objective_value = float(lines[-1])
        for line in lines[:-1]:
            [flow_id, mirror_switch_id] = line.split(" ")
            flow_id = int(flow_id)
            mirror_switch_id = int(mirror_switch_id)
            solution_def = SolutionDefinition(flow_id, mirror_switch_id, objective_value)
            solutions[flow_id] = solution_def
        
        return solutions

    def __str__(self):
        s = "Flows:\n"
        for flow in self._flows.values():
            s += "\t%s\n" % str(flow)
        s += "\nSolutions:\n"
        for solution in self._approx_solutions.values():
            s += "\t%s\n" % str(solution)
        return s

class TrialProvider:
    def __init__(self, provider_name):
        self._provider_name = provider_name
        self._trials = []

    @property
    def name(self):
        return self._provider_name
    
    @staticmethod
    def create_provider(provider_name):
        return TrialProvider(provider_name)
    
    def add_trial(self, trial):
        self._trials.append(trial)
        return self

    def __iter__(self):
        return iter(self._trials)
