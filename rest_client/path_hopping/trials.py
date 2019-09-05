
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

def attempted_optimal(target_graph):
    the_trial_provider = trial_provider.TrialProvider("optimal")
    flow_set = FlowSet()
    the_trial = trial_provider.Trial("optimal")
    flow_allocation_seed_number, flows, link_utilization = flow_allocation.compute_optimal_flow_allocations(
            target_graph)
    flow_set.add_flows(flows)
    the_trial.add_parameter("K", 3)
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


