
import numpy                                as np
import random                               as rand
import scipy.stats                          as ss

import nw_control.trial_provider            as trial_provider
import path_hopping.flow_allocation         as flow_allocation

from path_hopping.flow_allocation           import FlowSet

def path_hopping_various_k_values(target_graph):
    the_trial_provider = trial_provider.TrialProvider("varying-k-values")
    for k_value in range(3, 11, 2):
        flow_set = FlowSet()
        the_trial = trial_provider.Trial("varying-k-values-%d" % k_value)
        the_trial.add_parameter("K", k_value)
        flow_allocation_seed_number, flows = flow_allocation.compute_equal_flow_allocations(
                target_graph, k_value)
        flow_set.add_flows(flows)
        the_trial.add_parameter("duration", 180)
        the_trial.add_parameter("flow-set", flow_set)
        the_trial.add_parameter("seed-number", flow_allocation_seed_number)
        the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def single_path_routing(target_graph):
    the_trial_provider = trial_provider.TrialProvider("single-path-routing")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("single-path-routing")
    flow_allocation_seed_number, flows = flow_allocation.compute_equal_flow_allocations(
            target_graph, 1)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", 1)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def path_hopping_flows(target_graph, K=3):
    the_trial_provider = trial_provider.TrialProvider("path-hopping")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("path-hopping")
    flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_path_hopping_flows_ilp(target_graph, K=3)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", K)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def flow_allocation_tests(target_graph, number_of_flows):
    the_trial_provider = trial_provider.TrialProvider("testing")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("testing")
    flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_test_flow_allocations(target_graph, number_of_flows)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", 3)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def greedy_path_hopping_flows(target_graph, K=3):
    the_trial_provider = trial_provider.TrialProvider("greedy")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("greedy")
    flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_optimal_flow_allocations(target_graph, K)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", K)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider 

def attempted_optimal_flows(target_graph):
    the_trial_provider = trial_provider.TrialProvider("optimal-varying-k")
    flow_set = FlowSet()
    for K in range(3, 4):
        the_trial = trial_provider.Trial("optimal-%d" % K)
        flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_optimal_flow_allocations(target_graph, K)
        flow_set.add_flows(flows)
        the_trial.add_parameter("K", K)
        the_trial.add_parameter("duration", 180)
        the_trial.add_parameter("flow-set", flow_set)
        the_trial.add_parameter("seed-number", flow_allocation_seed_number)
        the_trial.add_parameter("link-utilization", link_utilization)
        the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def ilp_flows(target_graph, K=3):
    def uniform_selection(node_list):
        [source_node, destination_node] = np.random.choice(node_list, 2, replace=False)
        return source_node, destination_node

    def non_uniform_selection(discrete_probability_distribution, node_list):
        [source_node, destination_node] = np.random.choice(node_list, size=2, replace=False,
                p=discrete_probability_distribution)
        return source_node, destination_node

    def mk_binomial_probability_distribution(node_set):
        discrete_probability_distribution = [ss.binom.pmf(node_id, len(node_set), 0.5)
                for node_id in node_set]
        discrete_probability_distribution[-1] += 1 - sum(discrete_probability_distribution)
        return discrete_probability_distribution

    def mk_uniform_probability_distribution(node_set):
        discrete_probability_distribution = [1.0/len(node_set) for _ in node_set]
        return discrete_probability_distribution

    flow_selection_fn = lambda node_list: non_uniform_selection(
            mk_uniform_probability_distribution(node_list), node_list)
    the_trial_provider = trial_provider.TrialProvider("ilp-flows")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("ilp")
    flow_allocation_seed_number = rand.randint(0, 2**32)
    flows, link_utilization = flow_allocation.compute_ilp_flows(
            target_graph, K, flow_selection_fn, seed_number=flow_allocation_seed_number)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", K)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def mcf_flows(target_graph):
    the_trial_provider = trial_provider.TrialProvider("multiflow-tests")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("mcf")
    flow_allocation_seed_number, flows, link_utilization =flow_allocation.compute_mcf_flows(
            target_graph)
    flow_set.add_flows(flows)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def path_hopping_mcf_flows(target_graph, K=3):
    the_trial_provider = trial_provider.TrialProvider("multiflow-tests")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("path-hopping-mcf")
    flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_path_hopping_flows_ilp(target_graph, K)
    flow_set.add_flows(flows)
    the_trial.add_parameter("duration", 180)
    the_trial.add_parameter("flow-set", flow_set)
    the_trial.add_parameter("seed-number", flow_allocation_seed_number)
    the_trial.add_parameter("link-utilization", link_utilization)
    the_trial.add_parameter("K", K)
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def multiflow_tests(target_graph, node_selection_type, K=3):
    NUMBER_OF_TRIALS = 10
    def uniform_selection(node_list):
        [source_node, destination_node] = np.random.choice(node_list, 2, replace=False)
        return source_node, destination_node

    def non_uniform_selection(discrete_probability_distribution, node_list):
        [source_node, destination_node] = np.random.choice(node_list, size=2, replace=False,
                p=discrete_probability_distribution)
        return source_node, destination_node

    def mk_binomial_probability_distribution(node_set):
        discrete_probability_distribution = [ss.binom.pmf(node_id, len(node_set), 0.5)
                for node_id in node_set]
        discrete_probability_distribution[-1] += 1 - sum(discrete_probability_distribution)
        return discrete_probability_distribution

    def mk_uniform_probability_distribution(node_set):
        discrete_probability_distribution = [1.0/len(node_set) for _ in node_set]
        return discrete_probability_distribution

    if node_selection_type == "binomial":
        discrete_probability_distribution = mk_binomial_probability_distribution(target_graph.nodes)
        FLOW_SELECTOR = lambda node_list: non_uniform_selection(discrete_probability_distribution,
                node_list)
    elif node_selection_type == "uniform":
        discrete_probability_distribution = mk_uniform_probability_distribution(target_graph.nodes)
        FLOW_SELECTOR = uniform_selection

    def k_paths_allocation(target_graph, K, flow_allocation_seed_number):
        flow_set = FlowSet()
        k_paths_trial = trial_provider.Trial("k-paths-allocation")
        flows, link_utilization = flow_allocation.compute_ilp_flows(
                target_graph, K, FLOW_SELECTOR, seed_number=flow_allocation_seed_number)
        flow_set.add_flows(flows)
        k_paths_trial.add_parameter("duration", 180)
        k_paths_trial.add_parameter("flow-set", flow_set)
        k_paths_trial.add_parameter("seed-number", flow_allocation_seed_number)
        k_paths_trial.add_parameter("link-utilization", link_utilization)
        k_paths_trial.add_parameter("K", K)
        return k_paths_trial

    def path_hopping_allocation(target_graph, K, flow_allocation_seed_number):
        flow_set = FlowSet()
        path_hopping_trial = trial_provider.Trial("path-hopping-allocation")
        flows, link_utilization = flow_allocation.compute_path_hopping_flows_ilp(target_graph, K, FLOW_SELECTOR, seed_number=flow_allocation_seed_number)
        flow_set.add_flows(flows)
        path_hopping_trial.add_parameter("duration", 180)
        path_hopping_trial.add_parameter("flow-set", flow_set)
        path_hopping_trial.add_parameter("seed-number", flow_allocation_seed_number)
        path_hopping_trial.add_parameter("link-utilization", link_utilization)
        path_hopping_trial.add_parameter("K", K)
        return path_hopping_trial

    def mcf_allocation(target_graph, flow_allocation_seed_number):
        flow_set = FlowSet()
        mcf_trial = trial_provider.Trial("mcf-trial")
        flows, link_utilization = flow_allocation.compute_mcf_flows(
                target_graph, FLOW_SELECTOR, seed_number=flow_allocation_seed_number)
        flow_set.add_flows(flows)
        mcf_trial.add_parameter("duration", 180)
        mcf_trial.add_parameter("flow-set", flow_set)
        mcf_trial.add_parameter("seed-number", flow_allocation_seed_number)
        mcf_trial.add_parameter("link-utilization", link_utilization)
        return mcf_trial

    def greedy_path_hopping_allocation(target_graph, K, flow_allocation_seed_number):
        flow_set = FlowSet()
        path_hopping_trial = trial_provider.Trial("greedy-path-hopping")
        flows, link_utilization = flow_allocation.compute_greedy_flow_allocations(
                target_graph, K, FLOW_SELECTOR, seed_number=flow_allocation_seed_number)
        flow_set.add_flows(flows)
        path_hopping_trial.add_parameter("duration", 180)
        path_hopping_trial.add_parameter("flow-set", flow_set)
        path_hopping_trial.add_parameter("seed-number", flow_allocation_seed_number)
        path_hopping_trial.add_parameter("link-utilization", link_utilization)
        return path_hopping_trial
    
    the_trial_provider = trial_provider.TrialProvider("multiflow-tests-%s" % node_selection_type)

    for _ in range(NUMBER_OF_TRIALS):
        flow_allocation_seed_number = rand.randint(0, 2**32)
        the_trial_provider.add_trial(k_paths_allocation(target_graph, K, 
            flow_allocation_seed_number))
        the_trial_provider.add_trial(mcf_allocation(target_graph, flow_allocation_seed_number))
        the_trial_provider.add_trial(greedy_path_hopping_allocation(target_graph, 9, 
            flow_allocation_seed_number))
    # the_trial_provider.add_trial(path_hopping_allocation(target_graph, K))

    the_trial_provider.add_metadata("node-probability-distribution", 
            discrete_probability_distribution)
    the_trial_provider.add_metadata("substrate-topology", target_graph)
    the_trial_provider.add_metadata("node-selection-type", node_selection_type)

    return the_trial_provider

def multiflow_tests_binomial(substrate_topology):
    return multiflow_tests(substrate_topology, "binomial")

def multiflow_tests_uniform(substrate_topology):
    return multiflow_tests(substrate_topology, "uniform")







