
import random           as rand
import pprint           as pp

class Trial:
    def __init__(self, name):
        self._name          = name
        self._parameters    = { "trial-name"    : name
                              , "id"            : str(rand.randint(0, 2**64))
                              }

    @property
    def name(self):
        return self._name

    def add_parameter(self, parameter_name, parameter_value):
        if parameter_name in self._parameters:
            raise ValueError("Name conflict for parameter with name %s",
                    parameter_name)
        self._parameters[parameter_name] = parameter_value

    def get_parameter(self, property_name):
        return self._parameters[property_name]

    def __str__(self):
        s = "Trial Name: %s\n" % self.name
        s += pp.pformat(self._parameters, indent=4)
        return s


class TrialProvider:
    def __init__(self, provider_name):
        self._provider_name     = provider_name
        self._trials             = []

    @property
    def provider_name(self):
        return self._provider_name

    @property
    def seed_number(self):
        return self._seed_number

    @property
    def trials(self):
        return self._trials 

    def add_trial(self, the_trial):
        self._trials.append(the_trial)

    def __iter__(self):
        for trial in self.trials:
            yield trial

    def __str__(self):
        s = ""
        for trial in self.trials:
            s += str(trial)
        return s













