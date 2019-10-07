
import numpy            as np
import networkx         as nx
import random           as rand
import pprint           as pp

import path_hopping_simulator.attackers     as attackers

from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths
from collections                                        import defaultdict

class PathHoppingSimulation:
    def __init__(self, nx_graph, nodes, flows, attacker_collection):
        self._ticks     = 0
        self._nodes     = {n_i.node_id: n_i for n_i in nodes}
        self._nx_graph  = nx_graph
        self._flows     = {f_i.flow_id: f_i for f_i in flows}
        self._attackers = attacker_collection

    @staticmethod
    def create(nx_graph, flow_count, attacker_collection):
        # @TODO: Determine values for N and K from G.
        flows = {PathHoppingFlow.create_random_flow(nx_graph, 9, 5) for _ in range(flow_count)}
        nodes = {PathHoppingNode(node_id) for node_id in nx_graph.nodes}
        the_path_hopping_simulation = PathHoppingSimulation(nx_graph, nodes, flows, 
                attacker_collection)
        return the_path_hopping_simulation
    
    def step(self):
        # Inject packets from source to ingress node
        for flow in self._flows.values():
            shares_for_flow = flow.create_shares()
            for share in shares_for_flow:
                self._nodes[flow.source_node].receive_share(share)

        # Move each packet one hop towards its destination
        node_id_to_shares_to_inject = defaultdict(set)
        for node in self._nodes.values():
            for share in node.resident_shares:
                next_hop = self._flows[share.flow_id].get_next_hop_for_share(share, node)
                if next_hop == -1:
                    self._flows[share.flow_id].receive_share(share)
                else:
                    node_id_to_shares_to_inject[next_hop].add(share)
            node.clear_resident_packets() 

        for node_id, shares_to_inject in node_id_to_shares_to_inject.items():
            for share in shares_to_inject:
                self._nodes[node_id].receive_share(share)
        
        # Allow each flow to hop
        for flow in self._flows.values():
            pass
            flow.hop()

        for attacker in self._attackers:
            attacker.monitor(self._nodes)
            attacker.select_monitored_nodes(self._nodes, self._flows)

    def print_state(self):
        print("Nodes: ")
        pp.pprint({n_i.node_id: n_i.resident_shares
            for n_i in self._nodes.values()})

        print("Flows: ")
        pp.pprint({f_i.flow_id: (("TX: %d" % f_i.messages_tx), ("RX: %d" % f_i.messages_rx))
            for f_i in self._flows.values()})

class PathHoppingShare:
    def __init__(self, flow_id, seq_num, share_num, source_node, sink_node):
        self._flow_id       = flow_id
        self._seq_num       = seq_num
        self._share_num     = share_num
        self._source_node   = source_node
        self._sink_node     = sink_node 

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def seq_num(self):
        return self._seq_num

    @property
    def share_num(self):
        return self._share_num 

    @property
    def source_node(self):
        return self._source_node

    @property
    def sink_node(self):
        return self._sink_node

    @staticmethod
    def create_shares_for( flow_id
                         , flow_source_node
                         , flow_sink_node
                         , seq_num
                         , K
                         , paths_for_message):
        return [PathHoppingShare(flow_id, seq_num, share_num, flow_source_node, flow_sink_node)
                for share_num in paths_for_message]

    def __str__(self):
        share_dict = { "flow_id"    : self.flow_id
                     , "seq_num"    : self.seq_num
                     , "share_num"  : self.share_num
                     }
        return pp.pformat(share_dict)

    def __repr__(self):
        return str(self)

class PathHoppingNode:
    def __init__(self, node_id):
        self._node_id           = node_id   
        self._resident_shares   = set()

    @property
    def node_id(self):
        return self._node_id

    @property
    def resident_shares(self):
        return self._resident_shares

    def vulnerable_shares(self):
        return [s_i for s_i in self.resident_shares 
                if s_i.source_node != self.node_id and s_i.sink_node != self.node_id]

    def receive_share(self, share):
        self._resident_shares.add(share)

    def clear_resident_packets(self):
        self._resident_shares = set()

    def remove_share(self, share):
        self._resident_shares.remove(share)

class PathHoppingFlow:
    _flow_id_counter = 0

    def __init__( self
                , source_node
                , sink_node
                , data_volume
                , paths
                , N
                , K):
        self._flow_id           = PathHoppingFlow._get_fresh_flow_id()
        self._source_node       = source_node
        self._sink_node         = sink_node
        self._paths             = paths 
        self._active_paths      = []
        self._data_volume       = data_volume
        self._N                 = N
        self._K                 = K
        self._seq_num           = 0
        self._shares_received   = {}
        self._messages_tx       = 0
        self._messages_rx       = 0

    @property
    def flow_id(self):
        return self._flow_id

    @property
    def source_node(self):
        return self._source_node

    @property
    def sink_node(self):
        return self._sink_node

    @property
    def messages_tx(self):
        return self._messages_tx

    @property
    def messages_rx(self):
        return self._messages_rx

    @staticmethod
    def create_random_flow( G
                          , N
                          , K
                          , min_data_volume = 1
                          , max_data_volume = 100):
        source_node, sink_node  = np.random.choice(G.nodes, 2, replace=False)
        flow_data_volume        = np.random.randint(min_data_volume, max_data_volume+1)
        print("Source %d, Sink %d, Volume %d" % (source_node, sink_node, flow_data_volume))
        paths                   = list(node_disjoint_paths(G, source_node, sink_node))
        if len(paths) < N:
            raise ValueError("Substrate cannot accommodate path hopping flow with N = %d \
                    (only %d disjoint paths between %d and %d)" %
                    (N, len(paths), source_node, sink_node))
        
        the_flow = PathHoppingFlow(source_node, sink_node, flow_data_volume, paths, N, K)
        # @TODO: Implement hopping and variable hopping rates.
        the_flow.hop()
        return the_flow

    @staticmethod
    def _get_fresh_flow_id():
        fresh_flow_id = PathHoppingFlow._flow_id_counter 
        PathHoppingFlow._flow_id_counter += 1
        return fresh_flow_id

    def get_next_hop_for_share(self, share, current_node):
        path_for_share = self._paths[share.share_num]
        current_hop_idx = path_for_share.index(current_node.node_id)
        next_hop_idx = current_hop_idx + 1
        if next_hop_idx == len(path_for_share):
            return -1
        return path_for_share[next_hop_idx]

    def get_next_seq_num(self):
        next_seq_num = self._seq_num
        self._seq_num += 1
        return next_seq_num

    def create_shares(self):
        self._messages_tx += 1
        seq_num_for_share = self.get_next_seq_num()
        self._shares_received[seq_num_for_share] = 0
        shares = PathHoppingShare.create_shares_for(self.flow_id, self.source_node, 
                self.sink_node, seq_num_for_share, self._K, self._active_paths)
        return shares

    def receive_share(self, share):
        self._shares_received[share.seq_num] += 1
        if self._shares_received[share.seq_num] == self._K:
            self._messages_rx += 1
            del self._shares_received[share.seq_num]

    def hop(self):
        # @TODO: Make hopping frequency adjustable
        self._active_paths = np.random.choice([idx for idx in range(len(self._paths))],
                self._K, replace=False)
