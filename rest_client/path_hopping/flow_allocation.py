
import nw_control.topo_mapper           as topo_mapper

import networkx             as nx
import pprint               as pp
import numpy                as np
import scipy                as sp
import json                 as json

from networkx.algorithms.shortest_paths.generic     import all_shortest_paths
from collections                                    import namedtuple

LINK_CAPACITY = 10

Flow = namedtuple("Flow", "source_node destination_node, flow_tx_rate")

def compute_flow_allocations(target_graph, K=3):
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
