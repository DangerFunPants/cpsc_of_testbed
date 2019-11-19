
import random                           as rand
import itertools                        as itertools

import nw_control.trial_provider       as trial_provider

def mk_trial_provider_with_params(basis_params, per_trial_params, title_fmt_string, provider_name):
    the_trial_provider = trial_provider.TrialProvider(provider_name)

    for run_idx, parameter_pack in enumerate(itertools.product(*basis_params)):
        parameter_pack = {key: value for key, value in parameter_pack}
        all_parameters = {**parameter_pack, **per_trial_params}
        all_parameters["run_idx"] = run_idx
        the_trial = trial_provider.Trial(
                title_fmt_string.format(**all_parameters))
        for param_name, param_value in all_parameters.items():
            the_trial.add_parameter(param_name, param_value)
        the_trial_provider.add_trial(the_trial)
    return the_trial_provider

def varying_path_length_fast_hops():
    number_of_runs = 10
    per_trial_params = { "K"                    : 5
                       , "N"                    : 10
                       , "attacker_hop_period"  : 1
                       , "sim_duration"         : 10**4
                       }
    basis_params = [ [("path_length", path_length) for path_length in range(1, 11)]
                   , [("seed_number", rand.randint(0, 2**32)) for _ in range(number_of_runs)]
                   ]
    title_fmt_string = "path-length-{path_length}-run-{run_idx}"
    trial_provider = mk_trial_provider_with_params(basis_params, per_trial_params, 
            title_fmt_string, "sim-path-length-fast-hops")
    return trial_provider

def varying_path_length_slow_hops():
    number_of_runs = 10
    per_trial_params = { "K"                    : 5
                       , "N"                    : 10
                       , "attacker_hop_period"  : 10
                       , "sim_duration"         : 10**4
                       }
    basis_params = [ [("path_length", path_length) for path_length in range(1, 11)]
                   , [("seed_number", rand.randint(0, 2**32)) for _ in range(number_of_runs)]
                   ]
    title_fmt_string = "path-length-{path_length}-run-{run_idx}"
    trial_provider = mk_trial_provider_with_params(basis_params, per_trial_params,
            title_fmt_string, "sim-path-length-slow-hops")
    return trial_provider

def varying_hop_period_long_paths():
    number_of_runs = 10
    per_trial_params = { "K"                    : 5
                       , "N"                    : 10
                       , "path_length"          : 10
                       , "sim_duration"         : 10**4
                       }
    basis_params = [ [("attacker_hop_period", hop_period) for hop_period in range(1, 11)]
                   , [("seed_number", rand.randint(0, 2**32)) for _ in range(number_of_runs)]
                   ]
    title_fmt_string = "hop-period-{attacker_hop_period}-run-{run_idx}" 
    trial_provider = mk_trial_provider_with_params(basis_params, per_trial_params,
            title_fmt_string, "sim-hop-period-long-paths")
    return trial_provider

def varying_hop_period_short_paths():
    number_of_runs = 10
    per_trial_params = { "K"                    : 5
                       , "N"                    : 10
                       , "path_length"          : 1
                       , "sim_duration"         : 10**4
                       }
    basis_params = [ [("attacker_hop_period", hop_period) for hop_period in range(1, 11)]
                   , [("seed_number", rand.randint(0, 2**32)) for _ in range(number_of_runs)]
                   ]
    title_fmt_string = "hop-period-{hop_period}-run-{run_idx}" 
    trial_provider = mk_trial_provider_with_params(basis_params, per_trial_params,
            title_fmt_string, "sim-hop-period-short-paths")
    return trial_provider

def varying_number_of_paths():
    NUMBER_OF_RUNS = 10

    the_trial_provider = trial_provider.TrialProvider("sim-number-of-paths-slow-hops")
    for number_of_paths in [i*10 for i in range(1, 11)]:
        for run_idx, seed_number in enumerate([rand.randint(0, 2**32)
            for _ in range(NUMBER_OF_RUNS)]):
            the_trial = trial_provider.Trial("number-of-paths-%d-run-%d" %
                    (number_of_paths, run_idx))
            the_trial.add_parameter("path-length", 5)
            the_trial.add_parameter("K", number_of_paths // 2)
            the_trial.add_parameter("N", number_of_paths)
            the_trial.add_parameter("attacker-hop-period", 10)
            the_trial.add_parameter("seed-number", seed_number)
            the_trial.add_parameter("sim-duration", 10**5)
            the_trial_provider.add_trial(the_trial)
    return the_trial_provider
