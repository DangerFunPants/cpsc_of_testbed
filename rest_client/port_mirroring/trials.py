
import port_mirroring.params                as pm_cfg
import port_mirroring.trial_provider        as trial_provider
import trials.flow_mirroring_trial          as flow_mirroring_trial
import trials.port_mirroring_trial          as port_mirroring_trial

def flow_mirroring_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("approx")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = flow_mirroring_trial.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, 300, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)
    
    return provider

def port_mirroring_trials():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("port_mirroring")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = port_mirroring_trial.PortMirroringTrial.create_trial(topology, 0.1, 0.5,
                flow_count, 300, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)

    return provider

def test_trial():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("optimal")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 4)]):
        trial = flow_mirroring_trial.FlowMirroringTrial.create_trial(topology, 0.1, 0.5, 
                flow_count, 30, "sub-trial-%d" % trial_idx)
        provider.add_trial(trial)
    
    return provider

