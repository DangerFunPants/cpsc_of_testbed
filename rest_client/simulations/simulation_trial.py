
import subprocess               as subprocess
import pathlib                  as path
import json                     as json
import pprint                   as pp

import simulations.simulation   as simulation

class SimulationTrial:
    SOLVER_PATH = path.Path("/home/cpsc-net-user/repos/virtual-link-embedding/")

    def __init__( self
                , number_of_nodes
                , number_of_flows
                , links_per_node
                , number_of_links
                , seed_number
                , solution_time
                , feasible):
        self._number_of_nodes   = number_of_nodes
        self._number_of_flows   = number_of_flows
        self._links_per_node    = links_per_node
        self._number_of_links   = number_of_links
        self._seed_number       = seed_number
        self._solution_time     = solution_time
        self._feasible          = feasible

    @property
    def number_of_nodes(self):
        return self._number_of_nodes

    @property
    def number_of_flows(self):
        return self._number_of_flows

    @property
    def links_per_node(self):
        return self._links_per_node

    @property
    def number_of_links(self):
        return self._number_of_links

    @property
    def seed_number(self):
        return self._seed_number

    @property
    def solution_time(self):
        return self._solution_time

    @property
    def feasible(self):
        return self._feasible

    @staticmethod
    def create_trial( number_of_nodes
                    , number_of_flows
                    , links_per_node
                    , seed_number):
        solver_results = SimulationTrial.invoke_solver_with_params(number_of_nodes,
                number_of_flows, links_per_node, seed_number)
        sim_trial = SimulationTrial(number_of_nodes, number_of_flows, links_per_node,
                solver_results.number_of_links, seed_number, solver_results.solution_time,
                solver_results.feasible)
        return sim_trial

    @staticmethod
    def invoke_solver_with_params( number_of_nodes
                                 , number_of_flows
                                 , links_per_node
                                 , seed_number):
        def create_solver_cmd( number_of_nodes
                             , number_of_flows
                             , links_per_node
                             , seed_number):
            base_cmd            = SimulationTrial.SOLVER_PATH.joinpath("invoke_solver.sh")
            input_file_path     = SimulationTrial.SOLVER_PATH.joinpath("flow-params.txt")
            input_file_json     = { "mode"                  : "simulation"
                                  , "number-of-nodes"       : number_of_nodes
                                  , "number-of-flows"       : number_of_flows
                                  , "links-per-node"        : links_per_node
                                  , "seed-number"           : seed_number
                                  }
            input_file_path.write_text(json.dumps(input_file_json))
            return [str(base_cmd)]
        
        cmd = create_solver_cmd(number_of_nodes, number_of_flows, links_per_node, seed_number)
        subprocess.run(cmd)
        trial_results_path = SimulationTrial.SOLVER_PATH.joinpath("simulation-%d.json" % seed_number)
        sim_trial = simulation.Simulation.from_json(trial_results_path.read_text())
        return sim_trial

    @staticmethod
    def to_dict(sim_object):
        dict_repr = { "number-of-nodes"     : sim_object.number_of_nodes
                    , "number-of-flows"     : sim_object.number_of_flows
                    , "links-per-node"      : sim_object.links_per_node
                    , "seed-number"         : sim_object.seed_number
                    , "solution-time"       : sim_object.solution_time
                    , "number-of-links"     : sim_object.number_of_links
                    , "feasible"            : sim_object.feasible
                    }
        return dict_repr

    @staticmethod
    def from_dict(sim_dict):
        the_sim = SimulationTrial(sim_dict["number-of-nodes"], sim_dict["number-of-flows"],
                sim_dict["links-per-node"], sim_dict["number-of-links"], sim_dict["seed-number"],
                sim_dict["solution-time"], sim_dict["feasible"])
        return the_sim

    @staticmethod
    def to_json(sim_object):
        return json.dumps(SimulationTrial.to_dict(sim_object))

    @staticmethod
    def from_json(sim_json):
        return SimulationTrial.from_dict(json.loads(sim_json))

    def __repr__(self):
        return pp.pformat(SimulationTrial.to_dict(self))

















