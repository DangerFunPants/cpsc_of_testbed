
import subprocess               as subprocess
import pathlib                  as path
import json                     as json

import mp_routing.params        as mp_cfg
import mp_routing.trial         as trial

class VleTrial:
    SOLVER_PATH = path.Path("/home/cpsc-net-user/repos/virtual-link-embedding/")
    
    def __init__( self
                , mean_flow_tx_rates
                , std_dev_flow_tx_rates
                , actual_flow_tx_rates
                , solver_results
                , seed_number):
        self._mean_flow_tx_rates        = mean_flow_tx_rates
        self._std_dev_flow_tx_rates     = std_dev_flow_tx_rates
        self._actual_flow_tx_rates      = actual_flow_tx_rates
        self._solver_results            = solver_results
        self._seed_number               = seed_number

    @property
    def mean_flow_tx_rates(self):
        return self._mean_flow_tx_rates

    @property
    def std_dev_flow_tx_rates(self):
        return self._std_dev_flow_tx_rates

    @property
    def actual_flow_tx_rates(self):
        return self._actual_flow_tx_rates

    @property
    def solver_results(self):
        return self._solver_results
    
    @property
    def seed_number(self):
        return self._seed_number

    @staticmethod
    def create_trial( mean_flow_tx_rates
                    , std_dev_flow_tx_rates
                    , actual_flow_tx_rates
                    , seed_number):
        solver_results = VleTrial.invoke_solver_with_params(mean_flow_tx_rates, 
                std_dev_flow_tx_rates, actual_flow_tx_rates, mp_cfg.link_capacity, 
                seed_number)
        # solver_results._flows = solver_results._flows[:30]
        vle_trial = VleTrial(mean_flow_tx_rates, std_dev_flow_tx_rates,
                actual_flow_tx_rates, solver_results, seed_number)
        return vle_trial

    @staticmethod
    def invoke_solver_with_params( mean_flow_tx_rates
                                 , std_dev_flow_tx_rates
                                 , actual_flow_tx_rates
                                 , link_capacity
                                 , seed_number):
        def create_solver_cmd( mean_flow_tx_rates
                             , std_dev_flow_tx_rates
                             , link_capacity
                             , seed_number):
            base_cmd = VleTrial.SOLVER_PATH.joinpath("invoke_solver.sh")
            flows_file_path = VleTrial.SOLVER_PATH.joinpath("flow-params.txt")
            flows_json_representation = { "mean-flow-tx-rates"      : mean_flow_tx_rates
                                        , "std-dev-flow-tx-rates"   : std_dev_flow_tx_rates
                                        , "actual-flow-tx-rates"         : actual_flow_tx_rates
                                        , "link-capacity"           : link_capacity
                                        , "seed-number"             : seed_number
                                        }
            flows_file_path.write_text(json.dumps(flows_json_representation))
            return [str(base_cmd)]

        cmd = create_solver_cmd(mean_flow_tx_rates, std_dev_flow_tx_rates, link_capacity,
                seed_number)
        subprocess.run(cmd)
        trial_results_path = VleTrial.SOLVER_PATH.joinpath("trial-%d.json" % seed_number)
        mp_routing_trial = trial.Trial.from_json(trial_results_path.read_text())
        return mp_routing_trial

    @staticmethod
    def to_dict(the_vle_trial):
        json_object = {}
        json_object["mean-flow-tx-rates"]       = the_vle_trial.mean_flow_tx_rates
        json_object["std-dev-flow-tx-rates"]    = the_vle_trial.std_dev_flow_tx_rates
        json_object["actual-flow-tx-rates"]     = the_vle_trial.actual_flow_tx_rates
        json_object["solver-results"]           = trial.Trial.to_dict(the_vle_trial.solver_results)
        json_object["seed-number"]              = the_vle_trial.seed_number

        return json_object

    @staticmethod
    def from_dict(vle_trial_dict):
        tx_rates        = vle_trial_dict["mean-flow-tx-rates"]
        std_dev         = vle_trial_dict["std-dev-flow-tx-rates"]
        actual_rates    = vle_trial_dict["actual-flow-tx-rates"]
        solver_results  = vle_trial_dict["solver-results"]
        seed_number     = vle_trial_dict["seed-number"]

        the_vle_trial = VleTrial(tx_rates, std_dev, actual_rates, solver_results, seed_number)
        return the_vle_trial

    @staticmethod
    def to_json(the_vle_trial):
        vle_trial_dict = VleTrial.to_dict(the_vle_trial)
        json_str = json.dumps(vle_trial_dict)
        return json_str

    @staticmethod
    def from_json(vle_trial_json_str):
        vle_trial_dict = json.loads(vle_trial_json_str)
        the_vle_trial = VleTrial.from_dict(vle_trial_dict)
        return the_vle_trial





























