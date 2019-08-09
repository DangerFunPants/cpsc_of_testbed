
import pprint               as pp
import json                 as json

class Simulation:
    def __init__( self
                , number_of_nodes
                , number_of_links
                , solution_time
                , feasible):
        self._number_of_nodes   = number_of_nodes
        self._number_of_links   = number_of_links
        self._solution_time     = solution_time
        self._feasible          = feasible

    @property
    def number_of_nodes(self):
        return self._number_of_nodes

    @property
    def number_of_links(self):
        return self._number_of_links

    @property
    def solution_time(self):
        return self._solution_time

    @property
    def feasible(self):
        return self._feasible

    @staticmethod
    def to_dict(simulation_object):
        dict_representation = { "number-of-nodes"   : simulation_object.number_of_nodes
                              , "number-of-links"   : simulation_object.number_of_links
                              , "solution-time"     : simulation_object.solution_time
                              , "feasible"          : simulation_object.feasible
                              }
        return dict_representation

    @staticmethod
    def from_dict(sim_dict):
        the_sim = Simulation(sim_dict["number-of-nodes"], sim_dict["number-of-links"],
                sim_dict["solution-time"], sim_dict["feasible"])
        return the_sim

    @staticmethod
    def to_json(sim_object):
        dict_repr = Simulation.to_dict(sim_object)
        return json.dumps(dict_repr)

    @staticmethod
    def from_json(sim_json):
        dict_repr = json.loads(sim_json)
        return Simulation.from_dict(dict_repr)
