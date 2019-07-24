
import pathlib          as path
import subprocess       as subprocess

from collections import namedtuple

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

FlowDefinition          = namedtuple("FlowDefinition", "flow_id traffic_rate, path")
SwitchDefinition        = namedtuple("SwitchDefinition", "switch_id resident_flows")
SolutionDefinition      = namedtuple("SolutionDefinition", "flow_id mirror_switch_id")

class FlowMirroringTrial:
    SOLVER_PATH         = path.Path("/home/cpsc-net-user/repos/flow-mirroring-scheme/")
    TOPOLOGY_FILE       = SOLVER_PATH.joinpath("network/temp-topo.txt")

    def __init__(self, topology, flows, switches, approx_solutions, optimal_solutions):
        self._topology              = topology
        self._flows                 = flows
        self._switches              = switches
        self._approx_solutions      = approx_solutions
        self._optimal_solutions     = optimal_solutions

    @staticmethod
    def create_trial(topology, minimum_flow_rate, maximum_flow_rate, num_flows):
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

        trial = FlowMirroringTrial(topology, flows, switches, approx_solutions, optimal_solutions)
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
        for line in lines[:-1]:
            [flow_id, mirror_switch_id] = line.split(" ")
            flow_id = int(flow_id)
            mirror_switch_id = int(mirror_switch_id)
            solution_def = SolutionDefinition(flow_id, mirror_switch_id)
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
    
    @staticmethod
    def create_provider(provider_name):
        return TrialProvider(provider_name)
    
    def add_trial(self, trial):
        self._trials.append(trial)
        return self

    def get_provider_name(self):
        return self._provider_name

    provider_name = property(get_provider_name)

    def __iter__(self):
        return iter(self._trials)
