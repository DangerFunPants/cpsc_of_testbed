
import pathlib              as path
import time                 as time
import json                 as json
import pprint               as pp
import random               as rand

import nw_control.results_repository    as rr
import simulations.simulation_trial     as simulation_trial
import simulations.params               as sim_cfg

def conduct_simulations(results_repository, seed_number, number_of_flows, node_counts):
    trials = []
    for number_of_nodes in node_counts:
        trial = simulation_trial.SimulationTrial.create_trial(number_of_nodes, 
                number_of_flows, 3, seed_number)
    
        schema_vars = { "flow-count"    : str(number_of_flows)
                      , "node-count"    : str(number_of_nodes) 
                      , "seed-number"   : str(seed_number)
                      }
        results_files = { "sim-results.json": simulation_trial.SimulationTrial.to_json(trial) }
        results_repository.write_trial_results(schema_vars, results_files)

def main():
    results_repository = rr.ResultsRepository.create_repository(sim_cfg.base_repository_path,
            sim_cfg.repository_schema, sim_cfg.repository_name)
    seed_numbers = [rand.randint(0, 2**32) for _ in range(10)]
    node_counts = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    flow_counts = [100, 500, 1000]
    for seed_number in seed_numbers:
        for flow_count in flow_counts:
            conduct_simulations(results_repository, seed_number, flow_count, node_counts)

    large_node_counts = [2500, 5000]
    for seed_number in seed_numbers:
        for flow_count in flow_counts:
            conduct_simulations(results_repository, seed_number, flow_count, large_node_counts)

    print(seed_numbers)

if __name__ == "__main__":
    main()
