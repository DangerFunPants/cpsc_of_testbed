
import numpy                    as np
import pprint                   as pp
import itertools                as itertools

class Attacker:
    def __init__(self, N, K, hop_period):
        self._monitored_nodes   = set()
        self._N                 = N
        self._K                 = K
        self._captured_shares   = []
        self._hop_period        = hop_period
        self._hop_count         = 0

    def monitor(self, nodes):
        for node_id in self._monitored_nodes:
            self.capture_shares(nodes[node_id])

    def capture_shares(self, node):
        self._captured_shares.extend(node.vulnerable_shares())

    def select_monitored_nodes(self):
        raise NotImplementedError("Don't instantiate PathHoppingAttacker!")

    def reconstruct_captured_messages(self):
        seq_num_selector = lambda s_i: s_i.seq_num
        captured_shares = sorted(self._captured_shares, key=seq_num_selector)
        captured_messages = []
        for seq_num, share_group in itertools.groupby(captured_shares, key=seq_num_selector):
            share_group = list(share_group)
            if len(share_group) == self._K:
                captured_messages.append(seq_num)
        return captured_messages

class RandomNodeHoppingAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        if self._node_collection == None:
            target_flow = flows[0]
            self._node_collection = sorted([n_i for n_i in nodes
                    if n_i != target_flow.source_node and n_i != target_flow.sink_node])

        if (simulation_time % self._hop_period) == 0:
            self._monitored_nodes = {node 
                    for node in np.random.choice(self._node_collection, self._K, replace=False)}
            self._hop_count += 1

    @staticmethod
    def create(N, K, G, flows, hop_period):
        the_random_attacker = RandomNodeHoppingAttacker(N, K, hop_period)
        the_random_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return the_random_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("The random node hopping attacker captured %d shares." % len(self._captured_shares))
        print("The random node hopping attacker recovered %d messages." % len(captured_messages))
        print("The random node hopping attacker hopped %d times." % self._hop_count)

class RandomPathHoppingAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_collection = []

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        # Attack exactly one flow 
        flow = flows[0]
        if len(self._node_collection) == 0:
            for p_i in flow.paths:
                if len(p_i) <= 2:
                    continue
                self._node_collection.append(p_i[1])

        # This probably isn't necessary
        self._node_collection = sorted(self._node_collection)
        if (simulation_time % self._hop_period) == 0:
            self._monitored_nodes = {node
                    for node in np.random.choice(self._node_collection, self._K, replace=False)}
            self._hop_count += 1

    @staticmethod
    def create(N, K, G, flows, hop_period):
        the_path_attacker = RandomPathHoppingAttacker(N, K, hop_period)
        the_path_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return the_path_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("The random path hopping attacker recovered %d shares." % len(self._captured_shares))
        print("The random path hopping attacker recevered %d messages." % len(captured_messages))
        print("The random path hopping attacker hopped %d times." % self._hop_count)
