
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

    def add_parameter( self
                     , parameter_name
                     , parameter_value):
        if parameter_name in self._parameters:
            raise ValueError("Name conflict for parameter with name %s",
                    parameter_name)
        self._parameters[parameter_name] = parameter_value

    def update_parameter( self
                        , parameter_name
                        , parameter_value):
        if parameter_name not in self._parameters:
            raise ValueError("Attempting to update non-existent parameter value.")

        self._parameters[parameter_name] = parameter_value

    def get_parameter(self, property_name):
        if property_name not in self._parameters:
            raise ValueError("Attempting to access non-existent property %s in trial with name %s" %
                    (property_name, self.name))
        return self._parameters[property_name]

    def has_parameter(self, parameter_name):
        return parameter_name in self._parameters

    def __str__(self):
        s = "Trial Name: %s\n" % self.name
        s += pp.pformat(self._parameters, indent=4)
        return s

    def __iter__(self):
        for property_name, property_value in self._parameters.items():
            yield (property_name, property_value)

    def __lt__(self, other):
        return self.name < other.name

class TrialProvider:
    def __init__(self, provider_name):
        self._provider_name     = provider_name
        self._trials            = []
        self._metadata          = {}

    @property
    def provider_name(self):
        return self._provider_name

    @property
    def trials(self):
        return self._trials 

    def add_trial(self, the_trial):
        self.trials.append(the_trial)

    def remove_trial(self, trial_to_remove):
        self.trials.remove(trial_to_remove)

    def get_first_trial_that_matches(self, match_fn):
        matching_trials = self.get_all_trials_that_match(match_fn)
        if len(matching_trials) == 0:
            raise ValueError("get_first_trial_that_matches could not find any matching trials.")
        return matching_trials[0]

    def get_all_trials_that_match(self, match_fn):
        matching_trials = [t_i for t_i in self.trials if match_fn(t_i)]
        return matching_trials

    def remove_all_trials_that_match(self, match_fn):
        matching_trials = self.get_all_trials_that_match(match_fn)
        for trial_to_remove in matching_trials:
            self.trials.remove(trial_to_remove)

    def add_metadata(self, metadata_key, metadata_value):
        if metadata_key in self._metadata:
            raise ValueError("Attempted to add duplicate key %s to trial provider %s" %
                    (metadata_key, self.provider_name))
        self._metadata[metadata_key] = metadata_value

    def get_metadata(self, metadata_key):
        if not (metadata_key in self._metadata):
            raise ValueError("Attempted to fetch non-existent metadata %s from provider %s" %
                    (metadata_key, self.provider_name))
        return self._metadata[metadata_key]

    def __iter__(self):
        for trial in self.trials:
            yield trial

    def __str__(self):
        s = ""
        for trial in self.trials:
            s += str(trial)
        return s

    def __eq__(self, other):
        return self._provider_name == other._provider_name

    def __len__(self):
        return len(self.trials)

class Flow:
    """
    Represents a flow with 
        * Source node
        * Destination node
        * Transmission rate
        * A set of paths through the substrate network. 
    """
    def __init__( self
                , source_node       = None
                , destination_node  = None
                , flow_tx_rate      = None
                , paths             = None
                , splitting_ratio   = None):
        self._source_node       = source_node
        self._destination_node  = destination_node
        self._flow_tx_rate      = flow_tx_rate
        self._paths             = paths
        self._splitting_ratio   = splitting_ratio

    @property
    def source_node(self):
        return self._source_node

    @property
    def destination_node(self):
        return self._destination_node

    @property
    def flow_tx_rate(self):
        return self._flow_tx_rate

    @property
    def paths(self):
        return self._paths

    @property
    def splitting_ratio(self):
        return self._splitting_ratio

class FlowSet:
    """
    Encapsulates a set of flows. Typically the set of flows will comprise a trial.
    """
    def __init__(self):
        self._flows     = []

    @property
    def flows(self):
        return self._flows

    def add_flow(self, flow):
        self._flows.append(flow)

    def add_flows(self, flows):
        self._flows.extend(flows)

    def __iter__(self):
        for flow in self.flows:
            yield flow

    def __str__(self):
        s = "Flow set with %d flows." % len(self.flows)
        return s

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.flows)
