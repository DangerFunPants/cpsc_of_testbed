
import pathlib          as path
import subprocess       as subprocess
import pprint           as pp
import json             as json

import port_mirroring.onos_rest_helpers     as onos_rest_helpers

from collections        import defaultdict

# How do I want this API to work? 
#   * Load a series of trials
#       * How to specify trials?
#       * Build a bunch of trial objects then aggregate them in a trial_provider
#         that can be consumed by the test runner.
#   * Query paramaters necessary to run the trials
#       * topology
#       * flows file
#       * switch file
#       * solution file
#
# How to build trial objects?
#   * initialize Trial object with parameters then invoke solvers.
#       * Need to run solvers in correct environment (python2.7 w/gurobipy)
#       * Could wrap solver in shell script then invoke shell script to 
#         generate outputs.

class TrialProvider:
    def __init__(self, provider_name):
        self._provider_name = provider_name
        self._trials = []

    @property
    def name(self):
        return self._provider_name

    @name.setter
    def name(self, name):
        self._provider_name = name

    def set_solution_type(self, soln_type):
        for trial in self._trials:
            trial.set_solution_type(soln_type)
    
    @staticmethod
    def create_provider(provider_name):
        return TrialProvider(provider_name)
    
    def add_trial(self, trial):
        self._trials.append(trial)
        return self

    def __iter__(self):
        for trial in self._trials:
            for trial_type in trial.get_solution_types():
                trial.set_solution_type(trial_type)
                yield trial
