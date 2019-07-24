
import port_mirroring.params                as pm_cfg
import port_mirroring.trial_provider        as trial_provider

def trial_one():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("trial-one")
    for flow_count in [idx*10 for idx in range(1, 6)]:
        trial = trial_provider.FlowMirroringTrial.create_trial(topology, 1, 5, flow_count)
        provider.add_trial(trial)
    
    return provider
