
import random                          as rand

import nw_control.trial_provider       as trial_provider

def varying_path_length():
    NUMBER_OF_RUNS = 10

    the_trial_provider = trial_provider.TrialProvider("sim-path-length-fast-hops")
    for path_length in range(1, 11):
        for run_idx, seed_number in enumerate([rand.randint(0, 2**32) 
            for _ in range(NUMBER_OF_RUNS)]):
            the_trial = trial_provider.Trial("path-length-%d-run-%d" % 
                    (path_length, run_idx))
            the_trial.add_parameter("path-length", path_length)
            the_trial.add_parameter("K", 5)
            the_trial.add_parameter("N", 10)
            the_trial.add_parameter("attacker-hop-period", 1)
            the_trial.add_parameter("seed-number", seed_number)
            the_trial.add_parameter("sim-duration", 10**5)
            the_trial_provider.add_trial(the_trial)

    return the_trial_provider

def varying_hop_period():
    NUMBER_OF_RUNS = 1

    the_trial_provider = trial_provider.TrialProvider("sim-hop-period-long-paths")
    # for hop_period in [n for n in range(1, 11)]:
    for hop_period in [1]:
        for run_idx, seed_number in enumerate([rand.randint(0, 2**32)
            for _ in range(NUMBER_OF_RUNS)]):
            the_trial = trial_provider.Trial("hop-period-%d-run-%d" %
                    (hop_period, run_idx))
            the_trial.add_parameter("path-length", 10)
            the_trial.add_parameter("K", 5)
            the_trial.add_parameter("N", 10)
            the_trial.add_parameter("attacker-hop-period", hop_period)
            the_trial.add_parameter("seed-number", seed_number)
            the_trial.add_parameter("sim-duration", 10**4)
            the_trial_provider.add_trial(the_trial)
    return the_trial_provider

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
