import of_processor as ofp
import host_mapper as mapper
import networkx as nx
import params as cfg
import ui_helpers as ui
import pprint as pp
import matplotlib.pyplot as plt

class GraphVisualizer:
    def __init__(self):
        pass

    def build_graph(self, adj_mat, sw_list, dpid_map):
        g = nx.Graph()
        # for sw_name in sw_list:
        #     g.add_node(sw_name, dpid = dpid_map[sw_name])
        for src_node, v in adj_mat.items():
            for dst_node, out_port in v.items():
                g.add_edge(src_node, dst_node, port = out_port)

        return g
                

def main():
    hm = mapper.HostMapper( [cfg.dns_server_ip]
                          , cfg.of_controller_ip
                          , cfg.of_controller_port
                          )
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    builder = GraphVisualizer()
    adj_mat = ui.get_friendly_adj_mat(of_proc, hm)
    dpid_map = ui.get_dpid_map(of_proc, hm)
    print('Adjacency Matrix:')
    pp.pprint(adj_mat)
    print('*******************************************************************')
    print('DPID Map:')
    pp.pprint(dpid_map)
    sw_list = list(dpid_map.keys())
    g = builder.build_graph(adj_mat, sw_list, dpid_map)
    print(g)
    nx.draw(g, pos=nx.spectral_layout(g), with_labels=True, node_size=500, font_size=18)
    # nx.draw_networkx_edge_labels(g, pos=nx.spring_layout(g), label_pos=0)
    plt.legend()
    plt.show()

if __name__ == '__main__':
    main()
