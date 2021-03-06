
import nw_control.topo_mapper           as topo_mapper

import networkx             as nx
import pprint               as pp
import numpy                as np
import scipy                as sp
import json                 as json
import itertools            as itertools
import gurobipy             as gp
import random               as rand
import sys                  as sys

from networkx.algorithms.shortest_paths.generic         import all_shortest_paths
from networkx.algorithms.connectivity.disjoint_paths    import node_disjoint_paths
from collections                                        import defaultdict
from sys                                                import stderr

# ************************* Global Flow Allocation Parameters *****************
LINK_CAPACITY               = 1.0
FLOW_TX_RATE_LOWER_BOUND    = 0.1
FLOW_TX_RATE_UPPER_BOUND    = 0.5
DEFAULT_SEED_NUMBER         = 0xCAFE_BABE
# *****************************************************************************


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

    def __len__(self):
        return len(self.flows)

def compute_path_hopping_flow_allocations(target_graph, K=3):
    """
    Returns a list of flows with randomly selected sources and destinations that 
    will saturate the network (i.e. a flow will be admitted provided that it would
    not cause the utilization of any link in the network to exceed 1. Flows are
    equally split across the K shortest paths connecting the source node to the 
    destination node.
    """
    flow_allocation_seed_number = 0xCAFE_BABE
    np.random.seed(flow_allocation_seed_number)
    # id_to_dpid          = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    link_utilization    = {(u, v): 0.0 for u, v in target_graph.edges}
    node_capacity       = {u: 0.0 for u in target_graph.nodes}
    flows               = []
    while True:
        source_node, destination_node = flow_selection_fn(target_graph.nodes, 2, replace=False)
        print(source_node, destination_node)

        shortest_paths = sorted(nx.all_simple_paths(target_graph, source_node, destination_node,
                cutoff=3),
                key=lambda p: len(p))
        k_shortest_paths = list(itertools.islice(shortest_paths, K))

        # flow_tx_rate = np.random.uniform() * 10
        flow_tx_rate = 1.0
        # if node_capacity[source_node] + flow_tx_rate > LINK_CAPACITY:
        #     break
        node_capacity[source_node] += flow_tx_rate
        capacity_was_exceeded = False  
        for path in [nx.utils.pairwise(p_i) for p_i in k_shortest_paths]:
            for u, v in [sorted(h_i) for h_i in path]:
                flow_rate_per_subpath = flow_tx_rate / K
                if (link_utilization[u, v] + flow_rate_per_subpath) > LINK_CAPACITY:
                    capacity_was_exceeded = True
                    break
                link_utilization[u, v] += flow_rate_per_subpath
            if capacity_was_exceeded:
                break

        if capacity_was_exceeded:
            break

        the_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = k_shortest_paths
                       , splitting_ratio    = [1.0/K]*K
                       )
        flows.append(the_flow)
    return flows, link_utilization

def compute_greedy_flow_allocations( target_graph
                                   , flow_selection_fn
                                   , seed_number=DEFAULT_SEED_NUMBER):
    """
    Returns a list of flows with randomly selected sources and destinations that
    will saturate the network (i.e. a flow will be addmitted provided that it will
    not cause the utilization of any link in the network to exceed 1. Flows are 
    split across the K least utilized paths connecting the source node to the 
    destination node (i.e. this is a greedy algorithm).
    """

    flow_allocation_seed_number = seed_number
    np.random.seed(flow_allocation_seed_number)

    link_utilization    = {tuple(sorted(link_tuple)): 0.0 for link_tuple in target_graph.edges}
    flows               = []

    while True:
        capacity_was_exceeded = False

        source_node, destination_node = flow_selection_fn(target_graph.nodes)
        flow_tx_rate = np.random.uniform(FLOW_TX_RATE_LOWER_BOUND, FLOW_TX_RATE_UPPER_BOUND)

        connecting_paths = list(node_disjoint_paths(target_graph, source_node, destination_node))
        disjoint_path_count = len(connecting_paths)
        flow_rate_per_subpath = flow_tx_rate / disjoint_path_count
        for path in [nx.utils.pairwise(p_i) for p_i in connecting_paths]:
            for u, v in [tuple(sorted(t_i)) for t_i in path]:
                if (link_utilization[u, v] + flow_rate_per_subpath) > LINK_CAPACITY:
                    capacity_was_exceeded = True
                    break
                link_utilization[u, v] += flow_rate_per_subpath
            if capacity_was_exceeded:
                break
        if capacity_was_exceeded:
            break

        the_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = connecting_paths
                       , splitting_ratio    = [1.0/disjoint_path_count]*disjoint_path_count
                       )
        flows.append(the_flow)
    return flows, link_utilization

def compute_test_flow_allocations(target_graph, number_of_flows, K=3):
    flow_allocation_seed_number = 123456789
    np.random.seed(flow_allocation_seed_number)
    link_utilization = {(u, v): 0.0 for u, v in target_graph.edges}
    flows = []
    [source_node] = np.random.choice(target_graph.nodes, 1, replace=False)
    destination_node_set = list(set(target_graph.nodes) - {source_node})
    for _ in range(number_of_flows):
        [destination_node] = np.random.choice(destination_node_set, 1, replace=False)
        shortest_paths = sorted(nx.all_simple_paths(target_graph, source_node, destination_node,
            cutoff=3),
            key=lambda p: len(p))
        k_shortest_paths = list(itertools.islice(shortest_paths, K))
        pp.pprint(k_shortest_paths)
        flow_tx_rate = 10.0
        for path in [nx.utils.pairwise(p_i) for p_i in k_shortest_paths]:
            for u, v in [sorted(h_i) for h_i in path]:
                flow_rate_per_subpath = flow_tx_rate / K
                link_utilization[u, v] += flow_rate_per_subpath

        the_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate / 10.0
                       , paths              = k_shortest_paths
                       , splitting_ratio    = [1.0/K]*K
                       )
        flows.append(the_flow)
    return flow_allocation_seed_number, flows, link_utilization

def compute_equal_flow_allocations(target_graph, K=3):
    """
    Returns a set of flows st. there will be a single flow sourced from each node in the
    network with a destination randomly chosen from the set V / {s} where V is the set of
    nodes in the graph and s is the source node of the flow. Flows are equally distributed
    over the three shortest paths connecting the source node to the destination node.
    """
    # id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
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

    # id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
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

def create_k_paths_model( target_topology
                        , flows
                        , new_source_node
                        , new_destination_node
                        , new_flow_tx_rate
                        , k_shortest_paths):
    path_allocation_model = gp.Model("path-allocation-model", gp.Env("gurobi.log"))
    
    new_flow = Flow( source_node        = new_source_node
                   , destination_node   = new_destination_node
                   , flow_tx_rate       = new_flow_tx_rate
                   , paths              = k_shortest_paths
                   , splitting_ratio    = None
                   )
    potential_flow_set = flows + [new_flow]

    # X: flow_index -> path_index -> splitting_ratio
    X = {}

    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        flow_routing_constraint_variable = gp.LinExpr(0.0)
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            X[flow_index, path_index] = path_allocation_model.addVar(name="X{%d,%d}" % 
                    (flow_index, path_index), lb=0.0, ub=1.0)
            flow_routing_constraint_variable += X[flow_index, path_index]
        path_allocation_model.addConstr(flow_routing_constraint_variable == 1.0, "frc%d" %
                flow_index)

    # ordered_list_of_edges = list(target_topology.edges)
    # link_set = {tuple(sorted(ordered_list_of_edges[idx])): idx 
    #         for idx in range(len(ordered_list_of_edges))}
    link_set = {tuple(sorted(link_tuple)): link_idx 
            for link_idx, link_tuple in enumerate(target_topology.edges)}
    # Y: flow_index -> link_index -> portion of flow bandwidth on link
    Y = {(flow_index, link_index): path_allocation_model.addVar(name="Y{%d,%d}" %
        (flow_index, link_index), lb=0.0, ub=1.0) 
        for flow_index, flow in enumerate(potential_flow_set) for link_index in link_set.values()}

    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            # forall. l_i in p_i.links
            for link_tuple in nx.utils.pairwise(path):
                link_index = link_set[tuple(sorted(link_tuple))]
                Y[flow_index, link_index] += X[flow_index, path_index] * flow.flow_tx_rate

    # T: flow_index -> link_index -> constraint_variable
    T = {}
    for (flow_index, link_index), y_ik in Y.items():
        T[flow_index, link_index] = path_allocation_model.addVar(name="T{%d, %d}" % 
                (flow_index, link_index), lb=0.0, ub=1.0)
        path_allocation_model.addConstr(T[flow_index, link_index] == y_ik)
    
    # U: link_index -> link_utilization
    alpha = path_allocation_model.addVar(name="alpha", lb=0.0, ub=1.0)
    path_allocation_model.addConstr(alpha >= 0.0)

    U = {link_index: path_allocation_model.addVar(name="U{%s}" % str(link_index))
            for link_index in link_set.values()}
    for (flow_index, link_index), y_fl in T.items():
        U[link_index] += y_fl

    K = {link_index: path_allocation_model.addVar(name="K{%s}" % str(link_index))
        for link_index in link_set.values()}

    for link_index, u_l in U.items():
        path_allocation_model.addConstr(K[link_index] == u_l)
        # Change the floating point literal in this line to change link capacity
        path_allocation_model.addConstr(K[link_index] <= (alpha * LINK_CAPACITY))

    path_allocation_model.setObjective(alpha, gp.GRB.MINIMIZE)

    return path_allocation_model

def variable_name_to_index_tuple(variable_name):
    if "X" in variable_name:
        return tuple([int(t_i) for t_i in variable_name[2:][:-1].split(",")])
    if "Y" in variable_name:
        return tuple([int(t_i) for t_i in variable_name[2:][:-1].split(",")])
    if "U" in variable_name:
        return int(variable_name[2:][:-1])
    if "K" in variable_name:
        return int(variable_name[2:][:-1])

def compute_ilp_flows( target_graph
                     , flow_selection_fn
                     , seed_number=DEFAULT_SEED_NUMBER):

    # id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = seed_number
    np.random.seed(flow_allocation_seed_number)
    flows = []
    
    feasible_model = None
    # flow_count = 0
    # flow_limit = 1000
    while True:
        source_node, destination_node = flow_selection_fn(target_graph.nodes)
        k_shortest_paths = list(node_disjoint_paths(target_graph, source_node, destination_node))
        flow_tx_rate = np.random.uniform(FLOW_TX_RATE_LOWER_BOUND, FLOW_TX_RATE_UPPER_BOUND)
        # flow_tx_rate = 1.0

        model_for_this_round = create_k_paths_model(target_graph, flows, source_node, destination_node, 
                flow_tx_rate, k_shortest_paths)
        model_for_this_round.optimize()
        if (model_for_this_round.status == gp.GRB.Status.INF_OR_UNBD or
                model_for_this_round.status == gp.GRB.Status.INFEASIBLE or
                model_for_this_round.status == gp.GRB.Status.UNBOUNDED):
            break

        print("Solved for %d flows" % (len(flows) + 1), file=stderr)
        feasible_model = model_for_this_round
        new_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = k_shortest_paths
                       , splitting_ratio    = []
                       )
        flows.append(new_flow)

    # Failed to embed even a single flow into the network.
    if feasible_model == None:
        return [], {}

    model_variables = feasible_model.getVars()
    ordered_list_of_links = list(target_graph.edges)
    link_set = {idx: ordered_list_of_links[idx] for idx in range(len(ordered_list_of_links))}
    # U: link_index -> link_utilization
    U = {}
    for v_i in model_variables:
        if "X" in v_i.varName:
            print(v_i)
            flow_index, path_index = variable_name_to_index_tuple(v_i.varName)
            flows[flow_index].splitting_ratio.append(v_i.x)
        elif "K" in v_i.varName:
            link_index = variable_name_to_index_tuple(v_i.varName)
            link_tuple = link_set[link_index]
            U[link_tuple] = v_i.x
        elif "alpha" == v_i.varName:
            print("Final value of alpha: %f" % v_i.x)
    
    print("Checking flows for weirdness")
    link_capacity_map = {link_tuple: 0.0 for link_tuple in target_graph.edges}
    for flow in flows:
        print(flow.splitting_ratio)
        if (sum(flow.splitting_ratio) != 1.0) or (len(flow.paths) != len(flow.splitting_ratio)):
            print("INVALID FLOW SPLITTING!!!")

        for path, splitting_ratio in zip(flow.paths, flow.splitting_ratio):
            for link in nx.utils.pairwise(path):
                sorted_link_tuple = tuple(sorted(link))
                link_capacity_map[sorted_link_tuple] += (splitting_ratio * flow.flow_tx_rate)


    pp.pprint(link_capacity_map)
    return flows, link_capacity_map

def create_mcf_model( substrate_topology
                    , flows
                    , new_flow_source_node
                    , new_flow_destination_node
                    , new_flow_tx_rate):
    mcf_model = gp.Model("mcf-model", gp.Env("gurobi.log"))
    new_flow = Flow( source_node = new_flow_source_node
                   , destination_node = new_flow_destination_node
                   , flow_tx_rate = new_flow_tx_rate
                   , paths = None
                   , splitting_ratio = None
                   )
    potential_flow_set = flows + [new_flow]
    
    link_set = {link_tuple: link_idx 
            for link_idx, link_tuple in enumerate(substrate_topology.edges)}
    # F : flow_idx 
    #  -> source_node 
    #  -> destination_node 
    #  -> flow on link (source_node, destination_node)
    F = {(flow_idx, source_node, destination_node): mcf_model.addVar(name="F{%d,%d,%d}" %
        (flow_idx, source_node, destination_node)) 
        for flow_idx, _ in enumerate(potential_flow_set)
        for source_node, destination_node in link_set.keys()}

    for flow_idx, flow in enumerate(potential_flow_set):
        for u in substrate_topology.nodes:
            egress_flow = gp.LinExpr(0.0)
            ingress_flow = gp.LinExpr(0.0)
            for v in substrate_topology.neighbors(u):
                egress_flow += F[flow_idx, u, v]
                ingress_flow += F[flow_idx, v, u]
            if u == flow.source_node:
                # forall adjacent nodes sum == -1
                mcf_model.addConstr((egress_flow - ingress_flow) == 1.0)
            elif u == flow.destination_node:
                mcf_model.addConstr((ingress_flow - egress_flow) == 1.0)
            else:
                # forall adjacent nodes sum == 0
                mcf_model.addConstr((ingress_flow - egress_flow) == 0.0)

    U = {link_index: gp.LinExpr(0.0) for link_index in link_set.values()}
    for (flow_idx, source_node, destination_node) in F.keys():
        link_index = link_set[source_node, destination_node]
        U[link_index] += (F[flow_idx, source_node, destination_node] * 
                potential_flow_set[flow_idx].flow_tx_rate)
        # U[link_index] += F[flow_idx, source_node, destination_node]

    alpha = mcf_model.addVar(name="alpha", lb=0.0, ub=1.0)
    for u, v in {tuple(sorted(t_i)) for t_i in link_set.keys()}:
        one_direction = link_set[u, v]
        other_direction = link_set[v, u]
        mcf_model.addConstr((U[one_direction] + U[other_direction]) <= LINK_CAPACITY * alpha)

    mcf_model.setObjective(alpha, gp.GRB.MINIMIZE)
    return mcf_model, U, F

def compute_mcf_flows(target_graph, flow_selection_fn, seed_number=DEFAULT_SEED_NUMBER):
    substrate_topology = nx.DiGraph(target_graph)
    # id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = seed_number
    np.random.seed(flow_allocation_seed_number)
    flows = []
    
    feasible_model = None
    feasible_utilization = None
    while True:
        source_node, destination_node = flow_selection_fn(substrate_topology.nodes)
        flow_tx_rate = np.random.uniform(FLOW_TX_RATE_LOWER_BOUND, FLOW_TX_RATE_UPPER_BOUND)
        model_for_this_round, U, F = create_mcf_model(substrate_topology, flows, source_node, 
                destination_node, flow_tx_rate)
        model_for_this_round.optimize()
        
        if (model_for_this_round.status == gp.GRB.Status.INF_OR_UNBD or
                model_for_this_round.status == gp.GRB.Status.INFEASIBLE or
                model_for_this_round.status == gp.GRB.Status.UNBOUNDED):
            break

        alpha = model_for_this_round.getVarByName("alpha")
        print("Solved for %d flows with alpha %s" % ((len(flows) + 1), alpha.x), file=stderr)
        feasible_model = model_for_this_round
        feasible_utilization = U
        feasible_allocations = {k: v.x for k, v in F.items()}
        new_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = None
                       , splitting_ratio    = None
                       )
        flows.append(new_flow)

    if feasible_model == None:
        return [], {}

    link_set = {link_index: link_tuple 
            for link_index, link_tuple in enumerate(substrate_topology.edges)}
    U = {link_set[link_index]: link_util.getValue() for link_index, link_util in feasible_utilization.items()}
    bidirectional_utilization = defaultdict(float)
    for link_tuple, unidirectional_utilization in U.items():
        bidirectional_utilization[tuple(sorted(link_tuple))] += unidirectional_utilization

    do_f_sanity_checks(flows, feasible_allocations)
    flows_with_routes = compute_mcf_flow_routes(flows, feasible_allocations)
    
    return flows_with_routes, dict(bidirectional_utilization)

def create_path_hopping_ilp_model( substrate_topology
                                 , flows
                                 , new_flow_source_node
                                 , new_flow_destination_node
                                 , new_flow_tx_rate
                                 , new_flow_disjoint_paths
                                 , K):
    path_hopping_mcf_model = gp.Model("path-hopping-mcf-model", gp.Env("gurobi.log"))
    new_flow = Flow( source_node        = new_flow_source_node
                   , destination_node   = new_flow_destination_node
                   , flow_tx_rate       = new_flow_tx_rate
                   , paths              = new_flow_disjoint_paths
                   , splitting_ratio    = None
                   )
    potential_flow_set = flows + [new_flow]
    link_set = {tuple(sorted(link_tuple)): link_idx
            for link_idx, link_tuple in enumerate(substrate_topology.edges)}
    
    # X: flow_index -> path_index -> splitting_ratio
    X = {}
    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        flow_routing_constraint_variable = gp.LinExpr(0.0)
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            X[flow_index, path_index] = path_hopping_mcf_model.addVar(name="X{%d,%d}" % 
                    (flow_index, path_index), vtype=gp.GRB.SEMICONT, lb=(1.0/K), ub=(1.0/K))
            flow_routing_constraint_variable += X[flow_index, path_index]
        path_hopping_mcf_model.addConstr(flow_routing_constraint_variable == 1.0, "frc%d" %
                flow_index)

    # Y: flow_index -> link_index -> portion of flow bandwidth on link
    Y = {(flow_index, link_index): path_hopping_mcf_model.addVar(name="Y{%d,%d}" %
        (flow_index, link_index), lb=0.0, ub=1.0) 
        for flow_index, flow in enumerate(potential_flow_set) for link_index in link_set.values()}

    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            # forall. l_i in p_i.links
            for link_tuple in nx.utils.pairwise(path):
                link_index = link_set[tuple(sorted(link_tuple))]
                Y[flow_index, link_index] += (X[flow_index, path_index] * flow.flow_tx_rate)

    # T: flow_index -> link_index -> constraint_variable
    T = {}
    for (flow_index, link_index), y_ik in Y.items():
        T[flow_index, link_index] = path_hopping_mcf_model.addVar(name="T{%d, %d}" % 
                (flow_index, link_index), lb=0.0, ub=1.0)
        path_hopping_mcf_model.addConstr(T[flow_index, link_index] == y_ik)
    
    # U: link_index -> link_utilization
    alpha = path_hopping_mcf_model.addVar(name="alpha", lb=0.0, ub=1.0)
    path_hopping_mcf_model.addConstr(alpha >= 0.0)

    U = {link_index: path_hopping_mcf_model.addVar(name="U{%s}" % str(link_index))
            for link_index in link_set.values()}
    for (flow_index, link_index), y_fl in T.items():
        U[link_index] += y_fl

    K = {link_index: path_hopping_mcf_model.addVar(name="K{%s}" % str(link_index))
        for link_index in link_set.values()}

    for link_index, u_l in U.items():
        path_hopping_mcf_model.addConstr(K[link_index] == u_l)
        # Change the floating point literal in this line to change link capacity
        path_hopping_mcf_model.addConstr(K[link_index] <= (alpha * LINK_CAPACITY))

    path_hopping_mcf_model.setObjective(alpha, gp.GRB.MINIMIZE)
    return path_hopping_mcf_model

def compute_path_hopping_flows_ilp( target_graph
                                  , K
                                  , flow_selection_fn
                                  , seed_number=DEFAULT_SEED_NUMBER):
    flow_allocation_seed_number = seed_number
    np.random.seed(flow_allocation_seed_number)
    flows = []
    feasible_model = None
    while True:
        source_node, destination_node = flow_selection_fn(target_graph)
        flow_tx_rate = np.random.uniform(FLOW_TX_RATE_LOWER_BOUND, FLOW_TX_RATE_UPPER_BOUND)

        disjoint_paths = list(node_disjoint_paths(target_graph, source_node, destination_node))

        model_for_this_round = create_path_hopping_ilp_model(target_graph, flows, source_node,
                destination_node, flow_tx_rate, disjoint_paths, K)
        model_for_this_round.optimize()
        if (model_for_this_round.status == gp.GRB.Status.INF_OR_UNBD or
                model_for_this_round.status == gp.GRB.Status.INFEASIBLE or
                model_for_this_round.status == gp.GRB.Status.UNBOUNDED):
            break

        print("Solved for %d flows" % (len(flows) + 1), file=stderr)
        feasible_model = model_for_this_round
        new_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = disjoint_paths
                       , splitting_ratio    = []
                       )
        flows.append(new_flow)
    # Failed to embed even a single flow into the network
    if feasible_model == None:
        return [], {}

    link_set = {link_index: tuple(sorted(link_tuple))
            for link_index, link_tuple in enumerate(target_graph.edges)}
    model_variables = feasible_model.getVars()
    U = {}
    for v_i in model_variables:
        if "X" in v_i.varName:
            flow_index, path_index = variable_name_to_index_tuple(v_i.varName)
            flows[flow_index].splitting_ratio.append(v_i.x)
        elif "K" in v_i.varName:
            link_index = variable_name_to_index_tuple(v_i.varName)
            link_tuple = link_set[link_index]
            U[link_tuple] = v_i.x
        elif "alpha" == v_i.varName:
            print("Final value of alpha: %f" % v_i.x)

    return flows, U

def single_flow(substrate_topology):

    np.random.seed(DEFAULT_SEED_NUMBER)
    source_node, destination_node = np.random.choice(substrate_topology.nodes, 2, replace=False)
    disjoint_paths = list(node_disjoint_paths(substrate_topology, source_node, destination_node))
    flow_tx_rate = 0.5
    the_flow = Flow( source_node    = source_node
                   , destination_node   = destination_node
                   , flow_tx_rate       = flow_tx_rate
                   , paths              = disjoint_paths
                   , splitting_ratio    = [1.0] + [0 for _ in range(len(disjoint_paths)-1)]
                   )
    return DEFAULT_SEED_NUMBER, [the_flow]

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


def testing_k_paths_flow_allocation( target_graph
                                   , flow_selection_fn
                                   , seed_number=DEFAULT_SEED_NUMBER):

    # id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = seed_number
    np.random.seed(flow_allocation_seed_number)
    flows = []
    
    feasible_model = None
    # flow_count = 0
    # flow_limit = 1000
    while True:
        source_node, destination_node = flow_selection_fn(target_graph.nodes)
        k_shortest_paths = list(node_disjoint_paths(target_graph, source_node, destination_node))
        # flow_tx_rate = np.random.uniform(FLOW_TX_RATE_LOWER_BOUND, FLOW_TX_RATE_UPPER_BOUND)
        flow_tx_rate = 0.2

        model_for_this_round = create_test_k_paths_model(target_graph, flows, 
                source_node, destination_node, 
                flow_tx_rate, k_shortest_paths)
        model_for_this_round.optimize()
        if (model_for_this_round.status == gp.GRB.Status.INF_OR_UNBD or
                model_for_this_round.status == gp.GRB.Status.INFEASIBLE or
                model_for_this_round.status == gp.GRB.Status.UNBOUNDED):
            break

        print("Solved for %d flows" % (len(flows) + 1), file=stderr)
        feasible_model = model_for_this_round
        new_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = k_shortest_paths
                       , splitting_ratio    = []
                       )
        flows.append(new_flow)

    # Failed to embed even a single flow into the network.
    if feasible_model == None:
        return [], {}

    model_variables = feasible_model.getVars()
    ordered_list_of_links = list(target_graph.edges)
    link_set = {idx: ordered_list_of_links[idx] for idx in range(len(ordered_list_of_links))}
    # U: link_index -> link_utilization
    U = {}
    for v_i in model_variables:
        if "X" in v_i.varName:
            print(v_i)
            flow_index, path_index = variable_name_to_index_tuple(v_i.varName)
            flows[flow_index].splitting_ratio.append(v_i.x)
        elif "K" in v_i.varName:
            link_index = variable_name_to_index_tuple(v_i.varName)
            link_tuple = link_set[link_index]
            U[link_tuple] = v_i.x
        elif "alpha" == v_i.varName:
            print("Final value of alpha: %f" % v_i.x)
    
    print("Checking flows for weirdness")
    link_capacity_map = {link_tuple: 0.0 for link_tuple in target_graph.edges}
    for flow in flows:
        print(flow.splitting_ratio)
        if (sum(flow.splitting_ratio) != 1.0) or (len(flow.paths) != len(flow.splitting_ratio)):
            print("INVALID FLOW SPLITTING!!! sum was %f" % sum(flow.splitting_ratio))
            print("len(flow.paths) = %d, len(flow.splitting_ratio) = %d" %
                    (len(flow.paths), len(flow.splitting_ratio)))

        for path, splitting_ratio in zip(flow.paths, flow.splitting_ratio):
            for link in nx.utils.pairwise(path):
                sorted_link_tuple = tuple(sorted(link))
                link_capacity_map[sorted_link_tuple] += (splitting_ratio * flow.flow_tx_rate)


    pp.pprint(link_capacity_map)
    return flows, link_capacity_map

def create_test_k_paths_model( target_graph
                             , flows
                             , new_flow_source_node
                             , new_flow_destination_node
                             , new_flow_tx_rate
                             , disjoint_paths):
    path_allocation_model = gp.Model("path-allocation-model", gp.Env("gurobi.log"))
    
    new_flow = Flow( source_node        = new_source_node
                   , destination_node   = new_destination_node
                   , flow_tx_rate       = new_flow_tx_rate
                   , paths              = disjoint_paths
                   , splitting_ratio    = None
                   )
    potential_flow_set = flows + [new_flow]

    # X: flow_index -> path_index -> splitting_ratio
    X = {}

    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        flow_routing_constraint_variable = gp.LinExpr(0.0)
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            X[flow_index, path_index] = path_allocation_model.addVar(name="X{%d,%d}" % 
                    (flow_index, path_index), lb=0.0, ub=1.0)
            flow_routing_constraint_variable += X[flow_index, path_index]
        path_allocation_model.addConstr(flow_routing_constraint_variable == 1.0, "frc%d" %
                flow_index)

    # ordered_list_of_edges = list(target_topology.edges)
    # link_set = {tuple(sorted(ordered_list_of_edges[idx])): idx 
    #         for idx in range(len(ordered_list_of_edges))}
    link_set = {tuple(sorted(link_tuple)): link_idx 
            for link_idx, link_tuple in enumerate(target_topology.edges)}
    # Y: flow_index -> link_index -> portion of flow bandwidth on link
    Y = {(flow_index, link_index): path_allocation_model.addVar(name="Y{%d,%d}" %
        (flow_index, link_index), lb=0.0, ub=1.0) 
        for flow_index, flow in enumerate(potential_flow_set) for link_index in link_set.values()}

    # forall. f_i in flows
    for flow_index, flow in enumerate(potential_flow_set):
        # forall. p_i in f_i.paths
        for path_index, path in enumerate(flow.paths):
            # forall. l_i in p_i.links
            for link_tuple in nx.utils.pairwise(path):
                link_index = link_set[tuple(sorted(link_tuple))]
                Y[flow_index, link_index] += X[flow_index, path_index] * flow.flow_tx_rate

    # T: flow_index -> link_index -> constraint_variable
    T = {}
    for (flow_index, link_index), y_ik in Y.items():
        T[flow_index, link_index] = path_allocation_model.addVar(name="T{%d, %d}" % 
                (flow_index, link_index), lb=0.0, ub=1.0)
        path_allocation_model.addConstr(T[flow_index, link_index] == y_ik)
    
    # U: link_index -> link_utilization
    alpha = path_allocation_model.addVar(name="alpha", lb=0.0, ub=1.0)
    path_allocation_model.addConstr(alpha >= 0.0)

    U = {link_index: path_allocation_model.addVar(name="U{%s}" % str(link_index))
            for link_index in link_set.values()}
    for (flow_index, link_index), y_fl in T.items():
        U[link_index] += y_fl

    K = {link_index: path_allocation_model.addVar(name="K{%s}" % str(link_index))
        for link_index in link_set.values()}

    for link_index, u_l in U.items():
        path_allocation_model.addConstr(K[link_index] == u_l)
        # Change the floating point literal in this line to change link capacity
        path_allocation_model.addConstr(K[link_index] <= (alpha * LINK_CAPACITY))

    path_allocation_model.setObjective(alpha, gp.GRB.MINIMIZE)

    return path_allocation_model

def create_test_k_paths_model( target_topology
                             , flows
                             , new_source_node
                             , new_destination_node
                             , new_flow_tx_rate
                             , k_disjoint_paths):
    path_allocation_model = gp.Model("path-allocation-model", gp.Env("gurobi.log"))
    new_flow = Flow( source_node        = new_source_node
                   , destination_node   = new_destination_node
                   , flow_tx_rate       = new_flow_tx_rate
                   , paths              = k_disjoint_paths
                   , splitting_ratio    = None
                   )
    potential_flow_set = flows + [new_flow]

    X = {}
    for flow_index, flow in enumerate(potential_flow_set):
        flow_routing_constraint_variable = gp.LinExpr(0.0)
        for path_index, path in enumerate(flow.paths):
            X[flow_index, path_index] = path_allocation_model.addVar(name="X{%d,%d}" %
                    (flow_index, path_index), lb=0.0, ub=1.0)
            flow_routing_constraint_variable += X[flow_index, path_index]
        path_allocation_model.addConstr(flow_routing_constraint_variable == 1.0)
    
    link_set = {tuple(sorted(link_tuple)): link_idx
            for link_idx, link_tuple in enumerate(target_topology.edges)}
    # Y: flow_index -> link_index -> portion of flow on link
    Y = {(flow_index, link_index): path_allocation_model.addVar(name="Y{%d,%d}" %
        (flow_index, link_index), lb=0.0, ub=1.0)
        for flow_index, flow in enumerate(potential_flow_set) for link_index in link_set.values()}
    Y_rhs = {(flow_index, link_index): gp.LinExpr(0.0)
        for flow_index, flow in enumerate(potential_flow_set) for link_index in link_set.values()}
    for flow_idnex, flow in enumerate(potential_flow_set):
        for path_index, path in enumerate(flow.paths):
            for link_tuple in nx.utils.pairwise(path):
                link_index = link_set[tuple(sorted(link_tuple))]
                Y_rhs[flow_index, link_index] += X[flow_index, path_index] * flow.flow_tx_rate

    for (flow_index, link_index), y_ik in Y_rhs.items():
        path_allocation_model.addConstr(Y[flow_index, link_index] == y_ik)
    
    alpha = path_allocation_model.addVar("alpha", lb=0.0, ub=1.0)

    # U: link_index -> link_utilization
    U = {link_index: path_allocation_model.addVar(name="U{%s}" % str(link_index))
            for link_index in link_set.values()}
    for (flow_index, link_index), y_ik in Y_rhs.items():
        U[link_index] += y_ik

    for link_index, u_l in U.items():
        path_allocation_model.addConstr(u_l <= (alpha * LINK_CAPACITY))

    path_allocation_model.setObjective(alpha, gp.GRB.MINIMIZE)
    return path_allocation_model

def do_f_sanity_checks(flows, F):
    def compute_flow_indices(F):
        return {t_i[0] for t_i in F.keys()}
    def flow_selector(f_key):
        return f_key[0]

    list_of_keys = sorted(list(F.keys()), key=flow_selector)

    for flow_idx, g in itertools.groupby(list_of_keys, flow_selector):
        the_flow = flows[flow_idx]
        g = list(g)
        egress_sum = sum([F[flow_key] for flow_key in g if flow_key[1] == the_flow.source_node])
        ingress_sum = sum([F[flow_key] for flow_key in g 
            if flow_key[2] == the_flow.destination_node])
        print(egress_sum, ingress_sum)

def traverse_graph(F, f, s, t, u, sr):
    r"""
    RETURNS
        A set of paths, P. \forall p_i \in P, p_i begins at s and ends at t.
        The set also includes the proportion of flow f that should transit
        each path p_i \in P
    """
    def get_paths_for_flow(F, s, f):
        """
        RETURNS
            A set of outgoing links and corresponding splitting ratios for flow f
            at node s
        """
        links = [((u, v), split_ratio) 
                for (flow_id, u, v), split_ratio in F.items() 
                if flow_id == f and u == s and split_ratio > 0.001]
        return links
    
    if u == t:
        return [([t], sr)]

    outgoing_links = get_paths_for_flow(F, u, f)
    paths_to_t = []

    for ((current_node, next_hop), split_ratio) in outgoing_links:
        paths_from_u_to_t = traverse_graph(F, f, s, t, next_hop, split_ratio) 
        paths_to_t.extend(paths_from_u_to_t)

    paths_to_t_with_u = []
    for path in paths_to_t:
        nodes, sr = path
        new_path = [u] + nodes
        paths_to_t_with_u.append((new_path, sr))

    return paths_to_t_with_u

def traverse_graph_iterative(F, f, s, t):
    def get_paths_for_flow(F, s, f):
        """
        RETURNS
            A set of outgoing links and corresponding splitting ratios for flow f
            at node s
        """
        links = [((u, v), split_ratio) 
                for (flow_id, u, v), split_ratio in F.items() 
                if flow_id == f and u == s and split_ratio > 0.001]
        return links

    # paths_from_s_to_t: [(node_list, splitting_ratio)]
    paths_from_s_to_t = []

    incomplete_paths = [([s], 1.0)]
    while len(incomplete_paths) != 0:
        current_path, current_sr = incomplete_paths[0]
        incomplete_paths = incomplete_paths[1:]
        next_hops = get_paths_for_flow(F, current_path[-1], f)

        for (u, v), sr in next_hops:
            if v in current_path:
                print("path has a loop")
                continue
            new_path = current_path + [v]
            new_sr = sr if sr < current_sr else current_sr
            if v == t:
                paths_from_s_to_t.append((new_path, new_sr))
            else:
                incomplete_paths.append((new_path, new_sr))
    
    return paths_from_s_to_t

def compute_mcf_flow_routes(flows, F):
    def flow_selector(f_key):
        return f_key[0]

    list_of_keys = sorted(list(F.keys()), key=flow_selector)
    routes_for_flow_at_idx = []
    flows_with_routes = []
    for flow_idx, g in itertools.groupby(list_of_keys, flow_selector):
        the_flow = flows[flow_idx]
        g = list(g) # g is a generator and is consumed on use.
        routes = traverse_graph_iterative(F, flow_idx, the_flow.source_node,
                the_flow.destination_node)
        s = sum([p_i[1] for p_i in routes]) 
        if abs(s - 1.0) > 0.1:
            print("WEIRDNESS...", s)
            pp.pprint(routes)
        
        flow_with_routes = Flow( source_node        = the_flow.source_node
                               , destination_node   = the_flow.destination_node
                               , flow_tx_rate       = the_flow.flow_tx_rate
                               , paths              = [p_i[0] for p_i in routes]
                               , splitting_ratio    = [p_i[1] for p_i in routes]
                               )
        flows_with_routes.append(flow_with_routes)
    return flows_with_routes


















