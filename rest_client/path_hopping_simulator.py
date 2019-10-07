
import networkx             as nx
import numpy                as np

import path_hopping_simulator.simulator     as ph_sim

from path_hopping_simulator.attackers       import RandomPathHoppingAttacker
from path_hopping_simulator.attackers       import RandomNodeHoppingAttacker

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

def main():
    np.random.seed(0xCAFE_BABE)
    N = 10
    K = 5
    G, source_id, sink_id = build_n_parallel_graph(10, 3)

    flows = {ph_sim.PathHoppingFlow.create_random_flow(G, N, K, 
        source_node=source_id, sink_node=sink_id)}
    simulation = ph_sim.PathHoppingSimulation.create(G, flows)

    attackers = [ RandomNodeHoppingAttacker.create(N, K, G, simulation.flows, 2)
                , RandomPathHoppingAttacker.create(N, K, G, simulation.flows, 2)
                ]
    
    for attacker in attackers:
        simulation.add_attacker(attacker)

    for _ in range(10000):
        simulation.step()

    simulation.print_state()

    for attacker in attackers:
        attacker.print_state()

if __name__ == "__main__":
    main()
