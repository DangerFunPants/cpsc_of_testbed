
import pprint       as pp

from collections    import namedtuple

Path = namedtuple("Path", "nodes fraction")

class Flow(object):
    def __init__(self, source_node, destination_node, rate, variance):
        self._source_node       = source_node
        self._destination_node  = destination_node
        self._paths             = []
        self._rate              = rate
        self._variance          = variance

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
                    }
        return flow_json

    @staticmethod
    def from_json(json_object):
        source_node = json_object["source_node"]
        destination_node = json_object["destination_node"]
        rate = json_object["rate"]
        variance = json_object["variance"]
        flow = Flow(source_node, destination_node, rate, variance)
        for path in json_object["paths"]:
            flow.add_path(path["nodes"], path["fraction"])
        return flow

    def verify_flow(self):
        total_rate_transported = sum([path.fraction for path in self.paths])
        return (total_rate_transported - 1.0) < 1**-10

    def __str__(self):
        return pp.pformat(self.to_json())

class Trial(object):
    def __init__(self):
        self._flows = []

    def add_flow(self, flow):
        if not flow.verify_flow():
            raise ValueError("Attempted to create trial with invalid flow: %s" %
                    (str(flow)))
        self._flows.append(flow)

    @staticmethod
    def to_json(trial_object):
        trial_json = { "flows": [flow.to_json() for flow in trial_object._flows] }
        return trial_json

    @staticmethod
    def from_json(json_object):
        trial = Trial()
        for flow_json in json_object["flows"]:
            flow = Flow.from_json(flow_json)
            trial.add_flow(flow)
