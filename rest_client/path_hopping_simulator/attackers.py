
import numpy                    as np
import pprint                   as pp
import itertools                as itertools

class PathHoppingAttacker:
    def __init__(self, N, K):
        self._monitored_nodes   = set()
        self._N                 = N
        self._K                 = K
        self._captured_shares   = []
        self._last_hop_time     = 0

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

class RandomPathHoppingAttacker(PathHoppingAttacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_monitored_nodes(self, nodes, flows):
        self._monitored_nodes = {node 
                for node in np.random.choice(sorted(list(nodes.keys())), self._K, replace=False)}

    @staticmethod
    def create(N, K, G):
        the_random_attacker = RandomPathHoppingAttacker(N, K)
        the_random_attacker.select_monitored_nodes(G, None)
        return the_random_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("The random attacker captured %d shares." % len(self._captured_shares))
        print("The random attacker recovered %d messages." % len(captured_messages))
