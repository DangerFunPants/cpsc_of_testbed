
import pprint       as pp
import json         as json

from collections    import namedtuple

Path = namedtuple("Path", "nodes fraction")

class Flow(object):
    def __init__(self, source_node, destination_node, rate, variance, actual_tx_rates):
        self._source_node       = source_node
        self._destination_node  = destination_node
        self._paths             = []
        self._rate              = rate
        self._variance          = variance
        self._actual_tx_rates   = actual_tx_rates

    @property
    def source_node(self):
        return self._source_node

    @property
    def destination_node(self):
        return self._destination_node

    @property
    def rate(self):
        return self._rate

    @property
    def variance(self):
        return self._variance

    @property
    def actual_tx_rates(self):
        return self._actual_tx_rates

    @property
    def paths(self):
        return self._paths

    def add_path(self, nodes, demand_fraction):
        if len(nodes) < 2 or nodes[0] != self.source_node or nodes[-1] != self.destination_node:
            raise ValueError("Cannot add invalid path %s to flow from %d -> %d" %
                    (str(nodes), self.source_node, self.destination_node))
        self._paths.append(Path(nodes, demand_fraction))

    @staticmethod
    def to_json(flow_object):
        paths_json = []
        for path in flow_object.paths:
            path_json = { "nodes"       : path.nodes
                        , "fraction"    : path.fraction
                        }
            paths_json.append(path_json)

        flow_json = { "source_node"         : flow_object.source_node
                    , "destination_node"    : flow_object.destination_node
                    , "paths"               : paths_json
                    , "rate"                : flow_object.rate
                    , "variance"            : flow_object.variance
                    , "actual_tx_rates"     : flow_object.actual_tx_rates
                    }
        return flow_json

    @staticmethod
    def from_json(json_object):
        source_node         = json_object["source_node"]
        destination_node    = json_object["destination_node"]
        rate                = json_object["rate"]
        variance            = json_object["variance"]
        actual_tx_rates     = json_object["actual_tx_rates"]

        flow = Flow(source_node, destination_node, rate, variance, actual_tx_rates)
        for path in json_object["paths"]:
            flow.add_path(path["nodes"], path["fraction"])
        return flow

    @staticmethod
    def to_dict(flow_object):
        paths_dict = []
        for path in flow_object.paths:
            path_dict = { "nodes"       : path.nodes
                        , "fraction"    : path.fraction
                        }
            paths_dict.append(path_dict)

        flow_dict = { "source_node"         : flow_object.source_node
                    , "destination_node"    : flow_object.destination_node
                    , "paths"               : paths_dict
                    , "rate"                : flow_object.rate
                    , "variance"            : flow_object.variance
                    , "actual_tx_rates"     : flow_object.actual_tx_rates
                    }
        return flow_dict

    @staticmethod
    def from_dict(flow_dict):
        source_node         = flow_dict["source_node"]
        destination_node    = flow_dict["destination_node"]
        rate                = flow_dict["rate"]
        variance            = flow_dict["variance"]
        actual_tx_rates     = flow_dict["actual_tx_rates"]

        flow = Flow(source_node, destination_node, rate, variance, actual_tx_rates)
        for path in flow_dict["paths"]:
            flow.add_path(path["nodes"], path["fraction"])
        return flow

    def verify_flow(self):
        total_rate_transported = sum([path.fraction for path in self.paths])
        return (total_rate_transported - 1.0) < 1**-10

    def __str__(self):
        return pp.pformat(Flow.to_json(self))

    def repr(self):
        return pp.pformat(Flow.to_json(self))

class Trial(object):
    def __init__(self, seed):
        self._flows     = []
        self._seed      = seed

    @property
    def seed(self):
        return self._seed

    @property
    def flows(self):
        return self._flows

    def add_flow(self, flow):
        if not flow.verify_flow():
            raise ValueError("Attempted to create trial with invalid flow: %s" %
                    (str(flow)))
        self._flows.append(flow)

    def get_flow_defs(self):
        path_splits = []
        for flow in self.flows:
            splits = [path.fraction for path in flow.paths]
            path_splits.append((flow.source_node, flow.destination_node, splits, 
                (flow.rate, flow.variance)))
        return path_splits

    @staticmethod
    def to_dict(trial_object):
        trial_dict = { "flows": [Flow.to_dict(flow) for flow in trial_object.flows] 
                     , "seed"   : trial_object.seed
                     }
        return trial_dict

    @staticmethod
    def from_dict(trial_dict):
        trial = Trial(trial_dict["seed"])
        for flow_json in trial_dict["flows"]:
            flow = Flow.from_json(flow_json)
            trial.add_flow(flow)
        return trial


    @staticmethod
    def to_json(trial_object):
        trial_dict = Trial.to_dict(trial_object)
        return json.dumps(trial_dict)

    @staticmethod
    def from_json(json_str):
        json_object = json.loads(json_str)
        trial = Trial.from_dict(json_object)
        return trial

    def __repr__(self):
        return pp.pformat([Flow.to_json(flow_i) for flow_i in self.flows])
