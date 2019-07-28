
import pathlib                              as path

import port_mirroring.params                as pm_cfg
import port_mirroring.trial_provider        as trial_provider
import trials.flow_mirroring_trial          as flow_mirroring_trial
import trials.port_mirroring_trial          as port_mirroring_trial
import nw_control.results_repository        as rr

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
    provider = trial_provider.TrialProvider.create_provider("run-0")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 6)]):
        trial = port_mirroring_trial.PortMirroringTrial.create_trial(topology, 0.1, 0.5,
                flow_count, 60, "sub-trial-%d" % trial_idx)
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

def port_mirroring_test():
    topology = pm_cfg.target_topo_path.read_text()
    provider = trial_provider.TrialProvider.create_provider("run-0")
    for trial_idx, flow_count in enumerate([idx*10 for idx in range(1, 2)]):
        trial = port_mirroring_trial.PortMirroringTrial.create_trial(topology, 0.1, 0.5,
                flow_count, 60, "sub-trial-%d" % trial_idx)
        trial.solution_types = ["greedy"]
        provider.add_trial(trial)

    return provider

def re_run_trials():
    trial_name = "sub-trial-0"
    schema_variables = { "provider-name"        : "run-0"
                       , "trial-name"           : trial_name
                       , "solution-type"        : "greedy"
                       }
    base_repo_path = path.Path("/home/cpsc-net-user/repos/port-mirroring-results-test")
    repository = rr.ResultsRepository.create_repository(base_repo_path,
            pm_cfg.repository_schema, pm_cfg.repository_name)
    provider = trial_provider.TrialProvider.create_provider("run-0")
    trial = port_mirroring_trial.PortMirroringTrial.from_repository_files(repository,
            schema_variables, 5, trial_name)
    provider.add_trial(trial)
    return provider

