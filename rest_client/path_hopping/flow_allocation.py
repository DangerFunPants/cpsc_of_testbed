
import nw_control.topo_mapper           as topo_mapper

import networkx             as nx
import pprint               as pp
import numpy                as np
import scipy                as sp
import json                 as json
import itertools            as itertools
import gurobipy             as gp

from networkx.algorithms.shortest_paths.generic     import all_shortest_paths
from collections                                    import namedtuple
from sys                                            import stderr

LINK_CAPACITY = 1.0
NODE_CAPACITY = 100

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
    id_to_dpid          = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    link_utilization    = {(u, v): 0.0 for u, v in target_graph.edges}
    node_capacity       = {u: 0.0 for u in target_graph.nodes}
    flows               = []
    while True:
        [source_node, destination_node] = np.random.choice(target_graph.nodes, 2, replace=False)
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
    return flow_allocation_seed_number, flows, link_utilization

def compute_optimal_flow_allocations(target_graph, K):
    """
    Returns a list of flows with randomly selected sources and destinations that
    will saturate the network (i.e. a flow will be addmitted provided that it will
    not cause the utilization of any link in the network to exceed 1. Flows are 
    split across the K least utilized paths connecting the source node to the 
    destination node (i.e. this is a greedy algorithm).
    """
    def utilization_of_most_utilized_link_on_path(path, link_utilization):
        most_utilized_link = max([link_utilization[u, v] for u, v in
            [sorted(t_i) for t_i in nx.utils.pairwise(path)]])
        return most_utilized_link

    def compute_k_least_utilized_paths(connecting_paths, link_utilization, K):
        selected_paths = sorted(connecting_paths, 
                key=lambda p_i: utilization_of_most_utilized_link_on_path(p_i, link_utilization))[:K]
        return selected_paths

    flow_allocation_seed_number = 0xCAFE_BABE
    np.random.seed(flow_allocation_seed_number)

    id_to_dpid          = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    link_utilization    = {(u, v): 0.0 for u, v in target_graph.edges}
    node_capacity       = {u: 0.0 for u in target_graph.nodes}
    flows               = []

    while True:
        capacity_was_exceeded = False
        [source_node, destination_node] = np.random.choice(target_graph.nodes, 2, replace=False)
        connecting_paths = nx.all_simple_paths(target_graph, source_node, destination_node,
                cutoff=3)
        selected_paths = compute_k_least_utilized_paths(connecting_paths, link_utilization, K)
        flow_tx_rate = np.random.uniform()
        if node_capacity[source_node] + flow_tx_rate > NODE_CAPACITY:
            print("exceeded node capacity")
            break
        node_capacity[source_node] += flow_tx_rate
        for path in [nx.utils.pairwise(p_i) for p_i in selected_paths]:
            for u, v in [sorted(t_i) for t_i in path]:
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
                       , paths              = selected_paths
                       , splitting_ratio    = [1.0/K]*K
                       )
        flows.append(the_flow)
    return flow_allocation_seed_number, flows, link_utilization

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

def create_model( target_topology
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

    ordered_list_of_edges = list(target_topology.edges)
    link_set = {tuple(sorted(ordered_list_of_edges[idx])): idx 
            for idx in range(len(ordered_list_of_edges))}
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
                Y[flow_index, link_index] += X[flow_index, path_index]

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

def compute_ilp_flows(target_graph, K=3):

    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = 0xCAFE_BABE
    np.random.seed(flow_allocation_seed_number)
    flows = []
    
    feasible_model = None
    while True:
        [source_node, destination_node] = np.random.choice(target_graph.nodes, 2, replace=False)
        # [source_node, destination_node] = [0, 1]
        shortest_paths = sorted(nx.all_simple_paths(target_graph, source_node, destination_node,
                cutoff=3),
                key=lambda p: len(p))
        k_shortest_paths = list(itertools.islice(shortest_paths, K))
        flow_tx_rate = np.random.uniform()

        model_for_this_round = create_model(target_graph, flows, source_node, destination_node, 
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
        return flow_allocation_seed_number, [], None

    model_variables = feasible_model.getVars()
    ordered_list_of_links = list(target_graph.edges)
    link_set = {idx: ordered_list_of_links[idx] for idx in range(len(ordered_list_of_links))}
    # U: link_index -> link_utilization
    U = {}
    for v_i in model_variables:
        print(v_i)
        if "X" in v_i.varName:
            flow_index, path_index = variable_name_to_index_tuple(v_i.varName)
            flows[flow_index].splitting_ratio.append(v_i.x)
        elif "K" in v_i.varName:
            link_index = variable_name_to_index_tuple(v_i.varName)
            link_tuple = link_set[link_index]
            U[link_tuple] = v_i.x
        elif "alpha" == v_i.varName:
            print("Final value of alpha: %f" % v_i.x)

    return flow_allocation_seed_number, flows, U

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
    link_index_to_link_tuple = {link_idx: link_tuple 
            for link_tuple, link_idx in link_set.items()}
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
        U[link_index] += F[flow_idx, source_node, destination_node]

    alpha = mcf_model.addVar(name="alpha", lb=0.0, ub=1.0)
    for u, v in {tuple(sorted(t_i)) for t_i in link_set.keys()}:
        one_direction = link_set[u, v]
        other_direction = link_set[v, u]
        mcf_model.addConstr((U[one_direction] + U[other_direction]) <= 1.0 * alpha)

    mcf_model.setObjective(alpha, gp.GRB.MINIMIZE)
    return mcf_model, U

def compute_mcf_flows(target_graph):
    substrate_topology = nx.DiGraph(target_graph)
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    flow_allocation_seed_number = 0xCAFE_BABE
    np.random.seed(flow_allocation_seed_number)
    flows = []
    
    feasible_model = None
    feasible_utilization = None
    while True:
        [source_node, destination_node] = np.random.choice(substrate_topology.nodes, 2, replace=False)
        flow_tx_rate = np.random.uniform()
        model_for_this_round, U = create_mcf_model(substrate_topology, flows, source_node, 
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
        new_flow = Flow( source_node        = source_node
                       , destination_node   = destination_node
                       , flow_tx_rate       = flow_tx_rate
                       , paths              = None
                       , splitting_ratio    = None
                       )
        flows.append(new_flow)

    if feasible_model == None:
        return flow_allocation_seed_number, [], None

    link_set = {link_index: link_tuple for link_index, link_tuple in enumerate(substrate_topology)}
    # U = {}
    # for v_i in feasible_model.getVars():
    #     if "U" in v_i.varName:
    #         link_index = variable_name_to_index_tuple(v_i.var_name)
    #         link_tuple = link_set[link_index]
    #         U[link_tuple] = v_i.x


    U = {link_index: link_util.getValue() for link_index, link_util in feasible_utilization.items()}
    return flow_allocation_seed_number, flows, U

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
