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
        for src_node, v in adj_mat.items():
            for dst_node, out_port in v.items():
                g.add_edge(src_node, dst_node, port = out_port)
        return g
                

def draw_topology():
    hm = mapper.HostMapper( [cfg.dns_server_ip]
                          , cfg.of_controller_ip
                          , cfg.of_controller_port
                          )
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    builder = GraphVisualizer()
    adj_mat = ui.get_friendly_adj_mat(of_proc, hm)
    dpid_map = ui.get_dpid_map(of_proc, hm)
    sw_list = list(dpid_map.keys())
    g = builder.build_graph(adj_mat, sw_list, dpid_map)
    layout = nx.spectral_layout(g)
    nx.draw(g, layout, node_size=1000)
    labels = {}
    for sw in dpid_map.values():
        labels[sw] = '$%s$' % sw.split('_')[-1]
    nx.draw_networkx_labels(g, layout, labels, font_size=16)
    plt.show()
