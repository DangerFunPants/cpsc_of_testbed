

import pathlib                          as path

import nw_control.trial_provider        as trial_provider

def test_with_single_trial():
    the_trial_provider = trial_provider.TrialProvider("attacker-testing")
    the_trial = trial_provider.Trial("attacker-testing")
    the_trial.add_parameter("K", 3)
    the_trial.add_parameter("N", 10)
    the_trial.add_parameter("port", 11111)
    the_trial.add_parameter("input-file", 
            path.Path("/home/cpsc-net-user/repos/mtd-crypto-impl/data/random_byte_10MB"))
    the_trial.add_parameter("output-file", path.Path("./out.dat"))
    the_trial.add_parameter("message-size", 256)
    the_trial.add_parameter("timestep", 100)
    the_trial.add_parameter("lambda", 0)
    the_trial.add_parameter("reliable", "False")
    the_trial.add_parameter("hop", "host")
    the_trial_provider.add_trial(the_trial)
    return the_trial_provider
