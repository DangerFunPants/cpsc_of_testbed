
import numpy                    as np
import pprint                   as pp
import itertools                as itertools

from networkx.algorithms.connectivity.disjoint_paths import node_disjoint_paths

class Attacker:
    def __init__(self, N, K, hop_period, **kwargs):
        self._monitored_nodes   = set()
        self._N                 = N
        self._K                 = K
        self._captured_shares   = []
        self._hop_period        = hop_period
        self._hop_count         = 0

    @property
    def monitored_nodes(self):
        return self._monitored_nodes

    @property
    def captured_shares(self):
        return self._captured_shares

    @property
    def hop_count(self):
        return self._hop_count

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
            if len({s_i.share_num for s_i in share_group}) == self._K:
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
        print("******************************** RANDOM NODE **************************")
        print("The random node hopping attacker captured %d shares." % len(self._captured_shares))
        print("The random node hopping attacker recovered %d messages." % len(captured_messages))
        print("The random node hopping attacker hopped %d times." % self._hop_count)
        print("***********************************************************************\n")

class RandomPathHoppingAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        # Attack exactly one flow 
        flow = flows[0]
        if self._node_collection == None:
            self._node_collection = []
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
        print("******************************** RANDOM PATH **************************")
        print("The random path hopping attacker recovered %d shares." % len(self._captured_shares))
        print("The random path hopping attacker recovered %d messages." % len(captured_messages))
        print("The random path hopping attacker hopped %d times." % self._hop_count)
        print("***********************************************************************\n")

class IdealRandomPathHoppingAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        def build_paths_for_target_flow(target_flow):
            paths = []
            for p_i in target_flow.paths:
                paths.append(p_i[1:-1])
            return paths

        target_flow = flows[0]
        if self._path_collection == None:
            self._path_collection = build_paths_for_target_flow(target_flow)

        if (simulation_time % self._hop_period) == 0:
            monitored_paths = np.random.choice(range(len(self._path_collection)), 
                    self._K, replace=False)
            monitored_nodes = {n_i for p_i in monitored_paths for n_i in self._path_collection[p_i]}
            self._monitored_nodes = monitored_nodes
            self._hop_count += 1
    
    @staticmethod
    def create(N, K, G, flows, hop_period):
        the_ideal_attacker = IdealRandomPathHoppingAttacker(N, K, hop_period)
        the_ideal_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return the_ideal_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("******************************** RANDOM IDEAL *************************")
        print("The random ideal path hopping attacker recovered %d shares." % 
                len(self._captured_shares))
        print("The random ideal path hopping attacker recovered %d messages." %
                len(captured_messages))
        print("The random ideal path hopping attacker hopped %d times." % self._hop_count)
        print("***********************************************************************\n")

class OneNodePerPathAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        self._graph = kwargs["graph"]
        super().__init__(*args, **kwargs)
        self._path_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        target_flow = flows[0]
        if self._path_collection == None:
            self._path_collection = [p_i[1:-1] for p_i in target_flow.paths]

        # Select K paths, then select a single node on each of the paths.
        if simulation_time & self._hop_period == 0:
            k_paths = list(np.random.choice(range(len(self._path_collection)), 
                self._K, replace=False))
            monitored_nodes = {np.random.choice(p_i) 
                    for p_i in [self._path_collection[k_path_idx] for k_path_idx in k_paths]}
            self._monitored_nodes = monitored_nodes
            self._hop_count += 1

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("***************************** One Node per Path Attacker ***************")
        print(f"The one node per path attacker recovered {len(self._captured_shares)} shares.")
        print(f"The one node per path attacker recovered {len(captured_messages)} messages.")
        print(f"The one node per path hopping attacker hopped {self._hop_count} times.")
        print("************************************************************************")

    @staticmethod
    def create(N, K, G, flows, hop_period):
        one_node_per_path_attacker = OneNodePerPathAttacker(N, K, hop_period, graph=G)
        one_node_per_path_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return one_node_per_path_attacker

class FixedAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        target_flow = flows[0]
        if self._path_collection == None:
            self._path_collection = [p_i[1:-1] for p_i in target_flow.paths]
            k_paths = list(np.random.choice(range(len(self._path_collection)),
                self._K, replace=False))
            monitored_nodes = {np.random.choice(p_i)
                    for p_i in [self._path_collection[k_path_idx] for k_path_idx in k_paths]}
            self._monitored_nodes = monitored_nodes
            self._hop_count = 1

    @staticmethod
    def create(N, K, G, flows, hop_period):
        the_fixed_attacker = FixedAttacker(N, K, hop_period)
        the_fixed_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return the_fixed_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("*************************** Fixed Attacker *******************************")
        print(f"The fixed attacker recovered {len(self._captured_shares)} shares.")
        print(f"The fixed attacker recovered {len(captured_messages)} messages.")
        print(f"The fixed attacker hopped {self._hop_count}.")
        print("**************************************************************************")

class PlannedAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shares = {}
        self._flows = kwargs["flows"]
        self._nodes = kwargs["nodes"]
        self._active_paths = set()
        self._monitored_paths = set()
        self._hop_index = 1

    def select_monitored_nodes(self, nodes, flows, simulation_time):
        target_flow = self._flows[0]

        if (simulation_time % self._hop_period) == 0:
            if (self._hop_index >= max([len(p_i) for p_i in target_flow.paths]) or \
                    len(self._monitored_paths) == self._N):
                self._hop_index = 1
                self._active_paths = set()
                self._monitored_paths = set()

            nodes_at_hop = {p_i[self._hop_index] for p_i in target_flow.paths}
            monitored_paths = [target_flow.paths[path_idx] for path_idx in self._monitored_paths]
            monitored_nodes_at_hop = {p_i[self._hop_index] for p_i in monitored_paths}
            possible_nodes = list(nodes_at_hop - monitored_nodes_at_hop)
            
            if len(possible_nodes) <= self._K:
                self._monitored_nodes = possible_nodes
            else:
                self._monitored_nodes = list(
                        np.random.choice(possible_nodes, self._K, replace=False))

        self._hop_index += 1
        
    def capture_shares(self, node):
        shares = node.vulnerable_shares()
        paths = self._flows[0].paths

        path_idx_for_node = next(path_idx
                for path_idx, p_i in enumerate(paths)
                if node.node_id in p_i)
        self._monitored_paths.add(path_idx_for_node)

        if len(shares) > 0:
            corresponding_path = next(path_idx 
                    for path_idx, p_i in enumerate(paths)
                    if node.node_id in p_i)
            self._active_paths.add(corresponding_path)
        self._captured_shares.extend(shares)

    @staticmethod
    def create(N, K, G, flows, hop_period, nodes):
        the_planned_attacker = PlannedAttacker(N, K, hop_period, flows=flows, nodes=nodes)
        the_planned_attacker.select_monitored_nodes(G.nodes, flows, 0)
        return the_planned_attacker
        
    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print("*************************** Planned Attacker *******************************")
        print(f"The planned attacker recovered {len(self._captured_shares)} shares.")
        print(f"The planned attacker recovered {len(captured_messages)} messages.")
        print(f"The planned attacker hopped {self._hop_count}.")
        print("**************************************************************************")

class MatrixModelAttacker:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._nw_mat = kwargs["graph"]

class TotalAttacker(Attacker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node_collection = None

    def select_monitored_nodes(self, nodes, flows, simulation_time): 
        if len(self._monitored_nodes) == 0:
            target_flow = flows[0]
            self._monitored_nodes = {p_i[1] for p_i in target_flow.paths}

    @staticmethod
    def create(N, K, G, flows, hop_period):
        the_total_attacker = TotalAttacker(N, K, hop_period)
        the_total_attacker.select_monitored_nodes(G.nodes, flows, 1)
        return the_total_attacker

    def print_state(self):
        captured_messages = self.reconstruct_captured_messages()
        print(f"The total attacker recovered {len(captured_messages)} messages")
