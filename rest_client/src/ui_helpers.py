from collections import defaultdict

def mk_readable(adj_mat, hm):
    ret = defaultdict(dict)
    for src, v in adj_mat.items():
        src_sw_no = hm.map_dpid_to_sw(src)
        for dst, port in v.items():
            dst_sw_no = hm.map_dpid_to_sw(dst)
            ret[src_sw_no][dst_sw_no] = port
    return ret

def get_friendly_adj_mat(of_proc, hm):
    adj_mat = of_proc.get_topo_links().get_adj_mat()
    readable = mk_readable(adj_mat, hm)
    return readable

def get_dpid_map(of_proc, hm):
    sw_list = of_proc.get_switch_list()
    dpid_map = {}
    for dpid in sw_list:
        sw_name = hm.map_dpid_to_sw(dpid)
        dpid_map[dpid] = sw_name
    return dpid_map