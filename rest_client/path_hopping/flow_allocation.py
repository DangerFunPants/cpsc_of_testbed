
import nw_control.topo_mapper           as topo_mapper

import networkx             as nx
import pprint               as pp

def compute_flow_allocations():
    target_graph = nx.complete_graph(10)
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(target_graph)
    pp.pprint(id_to_dpid)

if __name__ == "__main__":
    main()

