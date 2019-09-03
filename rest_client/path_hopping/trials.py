
import nw_control.trial_provider            as trial_provider
import path_hopping.flow_allocation         as flow_allocation

from path_hopping.flow_allocation           import FlowSet

def path_hopping_various_k_values(target_graph):
    flow_set = FlowSet()
    the_trial_provider = trial_provider.TrialProvider("varying-k-values")
    for k_value in range(3, 11):
        the_trial = trial_provider.Trial("varying-k-values")
        the_trial.add_parameter("K", k_value)
        flow_allocation_seed_number, flows = flow_allocation.compute_equal_flow_allocations(
                target_graph, k_value)
        flow_set.add_flows(flows)
        the_trial.add_parameter("duration", 300)
        the_trial.add_parameter("flow-set", flow_set)
        the_trial.add_parameter("seed-number", flow_allocation_seed_number)
        the_trial_provider.add_trial(the_trial)
    return the_trial_provider



