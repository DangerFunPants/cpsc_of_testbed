
import networkx             as nx
import numpy                as np
import pathlib              as path

import path_hopping_simulator.simulator     as ph_sim
import path_hopping.params                  as ph_cfg
import nw_control.results_repository        as rr
import path_hopping_simulator.trials        as trials

from path_hopping_simulator.attackers       import RandomPathHoppingAttacker
from path_hopping_simulator.attackers       import RandomNodeHoppingAttacker
from path_hopping_simulator.attackers       import IdealRandomPathHoppingAttacker

def build_n_parallel_graph(number_of_paths, path_length):
    G = nx.Graph()

    paths = []
    node_id_counter = 0
    for n_i in range(number_of_paths):
        p_i = []
        for h_i in range(path_length):
            G.add_node(node_id_counter)
            p_i.append(node_id_counter)
            node_id_counter += 1
        paths.append(p_i)

    source_node = node_id_counter
    node_id_counter += 1
    sink_node = node_id_counter
    for p_i in paths:
        G.add_edge(source_node, p_i[0])
        G.add_edge(sink_node, p_i[-1])
        for u, v in zip(p_i, p_i[1:]):
            G.add_edge(u, v)
    return G, source_node, sink_node

def conduct_path_hopping_simulation(the_trial):
    N = the_trial.get_parameter("N")
    K = the_trial.get_parameter("K")
    np.random.seed(the_trial.get_parameter("seed-number")) 
    G, source_id, sink_id = build_n_parallel_graph(N, the_trial.get_parameter("path-length"))
    flows = {ph_sim.PathHoppingFlow.create_random_flow(G, N, K,
        source_node=source_id, sink_node=sink_id, flow_id=0)}
    simulation = ph_sim.PathHoppingSimulation.create(G, flows)
    attacker_hop_period = the_trial.get_parameter("attacker-hop-period")

    random_path_hopping_attacker = RandomPathHoppingAttacker.create(N, K, G, simulation.flows,
            attacker_hop_period)
    random_node_hopping_attacker = RandomNodeHoppingAttacker.create(N, K, G, simulation.flows,
            attacker_hop_period)
    ideal_random_path_hopping_attacker = IdealRandomPathHoppingAttacker.create(N, K, G, 
            simulation.flows, attacker_hop_period)
    attackers = [ random_path_hopping_attacker
                , random_node_hopping_attacker
                , ideal_random_path_hopping_attacker
                ]
    for attacker in attackers:
        simulation.add_attacker(attacker)

    for _ in range(the_trial.get_parameter("sim-duration")):
        simulation.step()

    simulation.print_state()

    for attacker in attackers:
        attacker.print_state()

    the_trial.add_parameter("random-path-hopping-attacker-recovered-messages",
            random_path_hopping_attacker.reconstruct_captured_messages())
    the_trial.add_parameter("random-node-hopping-attacker-recovered-messages",
            random_node_hopping_attacker.reconstruct_captured_messages())
    the_trial.add_parameter("ideal-random-path-hopping-attacker-recovered-messages",
            ideal_random_path_hopping_attacker.reconstruct_captured_messages())

def main():
    results_repository = rr.ResultsRepository.create_repository(
            path.Path("/home/cpsc-net-user/results-repositories/path-hopping-simulations"),
            ph_cfg.repository_schema, "path-hopping-simulations")
    trial_provider = trials.varying_path_length()
    for the_trial in trial_provider:
        conduct_path_hopping_simulation(the_trial)
    schema_vars = {"provider-name": trial_provider.provider_name}
    results_repository.write_trial_provider(schema_vars, trial_provider, overwrite=True)

if __name__ == "__main__":
    main()
