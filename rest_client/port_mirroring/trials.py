
import port_mirroring.params                as pm_cfg
import port_mirroring.trial_provider        as trial_provider

def trial_one():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("trial-one")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 4)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, pm_cfg.trial_length, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)
    
    return provider

def trial_two():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("trial-two")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 4)]):
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 1, 5, 
                flow_count, pm_cfg.trial_length, "sub-trial-%d" % (trial_idx + 1))
        provider.add_trial(trial)
    
    return provider

