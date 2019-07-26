
import port_mirroring.params                as pm_cfg
import port_mirroring.trial_provider        as trial_provider

def flow_mirroring_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("approx")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, 300, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)
    
    return provider

def optimal_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("optimal")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, pm_cfg.trial_length, "sub-trial-%d" % trial_idx)
        trial.set_solution_type("optimal")
        provider.add_trial(trial)
    
    return provider

def port_mirroring_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("port_mirroring")
    trial = trial_provider.PortMirroringTrial.create_trial(topology, 0.1, 0.5,
            10, 30, "sub-trial-1")
    provider.add_trial(trial)
    return provider

def all_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("approx")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, pm_cfg.trial_length, "sub-trial-%d" % trial_idx)
        trial.set_solution_type("approx")
        provider.add_trial(trial)
    
    return provider


def test_trial():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("optimal")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 4)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, 30, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)
    
    return provider

