
import networkx             as nx
import numpy                as np

import path_hopping_simulator.simulator     as ph_sim

from path_hopping_simulator.attackers       import RandomPathHoppingAttacker

def main():
    np.random.seed(0xCAFE_BABE)
    G = nx.complete_graph(10)
    attackers = [ RandomPathHoppingAttacker.create(9, 5, {n_i: 0 for n_i  in G.nodes})
                ]
    simulation = ph_sim.PathHoppingSimulation.create(G, 1, attackers)
    for _ in range(300):
        simulation.step()
    simulation.print_state()

    for attacker in attackers:
        attacker.print_state()

if __name__ == "__main__":
    main()
