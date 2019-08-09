
import pathlib              as path
import time                 as time
import json                 as json
import pprint               as pp

import nw_control.results_repository    as rr
import simulations.simulation_trial     as simulation_trial
import simulations.params               as sim_cfg

def conduct_simulations(results_repository, number_of_flows):
    trials = []
    for number_of_nodes in [100, 200, 300, 400, 500]:
        trial = simulation_trial.SimulationTrial.create_trial(number_of_nodes, 
                number_of_flows, 3, 4065)
    
        schema_vars = { "flow-count": str(number_of_flows), "node-count": str(number_of_nodes) }
        results_files = { "sim-results.json": simulation_trial.SimulationTrial.to_json(trial) }
        results_repository.write_trial_results(schema_vars, results_files)

def main():
    results_repository = rr.ResultsRepository.create_repository(sim_cfg.base_repository_path,
            sim_cfg.repository_schema, sim_cfg.repository_name)
    for flow_counts in [10, 100, 1000, 10000]:
        conduct_simulations(results_repository, 10)
    pass

if __name__ == "__main__":
    main()
