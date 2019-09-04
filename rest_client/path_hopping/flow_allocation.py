
import nw_control.topo_mapper           as topo_mapper

import networkx             as nx
import pprint               as pp
import numpy                as np
import scipy                as sp
import json                 as json
import itertools            as itertools

from networkx.algorithms.shortest_paths.generic     import all_shortest_paths
from collections                                    import namedtuple

LINK_CAPACITY = 10

class Flow:
    """
    Represents a flow with 
        * Source node
        * Destination node
        * Transmission rate
        * A set of paths through the substrate network. 
    """
    def __init__( self
                , source_node       = None
                , destination_node  = None
                , flow_tx_rate      = None
                , paths             = None
                , splitting_ratio   = None):
        self._source_node       = source_node
        self._destination_node  = destination_node
        self._flow_tx_rate      = flow_tx_rate
        self._paths             = paths
        self._splitting_ratio   = splitting_ratio

    @property
    def source_node(self):
        return self._source_node

    @property
    def destination_node(self):
        return self._destination_node

    @property
    def flow_tx_rate(self):
        return self._flow_tx_rate

    @property
    def paths(self):
        return self._paths

    @property
    def splitting_ratio(self):
        return self._splitting_ratio

class FlowSet:
    """
    Encapsulates a set of flows. Typically the set of flows will comprise a trial.
    """
    def __init__(self):
        self._flows     = []

    @property
    def flows(self):
        return self._flows

    def add_flow(self, flow):
        self._flows.append(flow)

    def add_flows(self, flows):
        self._flows.extend(flows)

    def __iter__(self):
        for flow in self.flows:
            yield flow

    def __str__(self):
        s = "Flow set with %d flows." % len(self.flows)
        return s

def compute_flow_allocations(target_graph, K=3):
    """
    Returns a list of flows with randomly selected sources and destinations that 
    will saturate the network (i.e. a flow will be admitted provided that it would
    not cause the utilization of any link in the network to exceed 1. Flows are
    equally split across the three shortest paths connecting the source node to the 
    destination node.
    """
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = 0xCAFE_BABE
    np.random.seed(flow_allocation_seed_number)
    link_utilization = {(u, v): 0.0 for u, v in target_graph.edges}
    flows = []
    while True:
        [source_node, destination_node] = np.random.choice(target_graph.nodes, 2, replace=False)
        shortest_paths = all_shortest_paths(target_graph,source_node, destination_node)
        flow_tx_rate = np.random.uniform()
        capacity_was_exceeded = False  
        for path in [nx.utils.pairwise(p_i) for p_i in shortest_paths]:
            for u, v in [sorted(h_i) for h_i in path]:
                if (link_utilization[u, v] + (flow_tx_rate / K)) > LINK_CAPACITY:
                    capacity_was_exceeded = True
                    break
                link_utilization[u, v] += flow_tx_rate / K
            if capacity_was_exceeded:
                break

        if capacity_was_exceeded:
            break

        flows.append(Flow(source_node.item(), destination_node.item(), flow_tx_rate))
    return flow_allocation_seed_number, flows

def compute_equal_flow_allocations(target_graph, K=3):
    """
    Returns a set of flows st. there will be a single flow sourced from each node in the
    network with a destination randomly chosen from the set V / {s} where V is the set of
    nodes in the graph and s is the source node of the flow. Flows are equally distributed
    over the three shortest paths connecting the source node to the destination node.
    """
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = 0xDEAD_BEEF
    np.random.seed(flow_allocation_seed_number)
    flows = []
    for node in target_graph.nodes:
        possible_destination_nodes = set(target_graph.nodes) - set([node])
        [destination_node] = np.random.choice(list(possible_destination_nodes), 1, replace=False)
        # shortest_paths = all_shortest_paths(target_graph, node, destination_node.item())
        shortest_paths = sorted(nx.all_simple_paths(target_graph, node, destination_node.item(),
                cutoff=3),
                key=lambda p: len(p))
        k_shortest_paths = list(itertools.islice(shortest_paths, K))
        the_flow = Flow( source_node        = node
                       , destination_node   = destination_node.item()
                       , flow_tx_rate       = 10.0
                       , paths              = k_shortest_paths
                       , splitting_ratio    = [1/K]*K
                       )
        flows.append(the_flow)
    
    return flow_allocation_seed_number, flows

def compute_unequal_flow_allocations(target_graph, K=3):
    """
    Returns a set of flows st. there will be a single flow sourced from each node in the 
    network with a destination randomly chosen from the set V / {s} where V is the set of nodes 
    in the graph and s is the source node of the flow. Flows are split over the three shortest
    paths connecting the sender to the receiver in such a way as to minimize the utilization
    of the most utilized link in the network.
    """

    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = 0xDEAD_BEEF
    np.random.seed(flow_allocation_seed_number)
    flows = []
    link_utilization = {}
    for node in target_graph.nodes:
        possible_destination_nodes = set(target_graph.nodes) - {node}
        destination_node = np.random.choice(list(possible_destination_nodes), 1, 
                replace=False).item()
        shortest_path = nx.shortest_path(target_graph, node, destination_node)
        the_flow = Flow( source_node        = node
                       , destination_node   = destination_node
                       , flow_tx_rate       = 10.0
                       , paths              = [shortest_path]
                       , splitting_ratio    = [1.0]
                       )
        flows.append(the_flow)

    return flow_allocation_seed_number, flows 


def create_flow_json(flows):
    def create_json_for_single_flow(flow):
        return { "source-node"          : flow.source_node
               , "destination-node"     : flow.destination_node
               , "flow-tx-rate"         : flow.flow_tx_rate
               }
    flow_dict_obj = [create_json_for_single_flow(flow) for flow in flows]
    return json.dumps(flow_dict_obj)

def parse_flows_from_json(json_str):
    flow_list = json.loads(json_str)
    return [Flow(flow_dict["source-node"], flow_dict["destination-node"], flow_dict["flow-tx-rate"])
            for flow_dict in flow_list]
