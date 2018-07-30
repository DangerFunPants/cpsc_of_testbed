import of_rest_client as of
import flowmod as fm
import pprint as p
import mp_route_adder as mp
from util import *
import host_mapper as mapper
import params as cfg
from collections import defaultdict

def query_flow_stats(dpid):
    req = of.SwitchFlows(dpid, cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    flows = resp.get_flows()
    print(resp)
    p.pprint(flows)

def query_switch_list():
    req = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    print(resp.switches)

def add_flow_mod():
    flow_mod = fm.Flowmod(5, hard_timeout=120)
    flow_mod.add_match(fm.Match(fm.MatchTypes.in_port, 2))
    flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port':1}))

    print(flow_mod)
    p.pprint(flow_mod.get_json())

    req = of.PushFlowmod(flow_mod, cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    print(resp)

def add_low_prio_flow_mod(dpid):
    flow_mod = fm.Flowmod(dpid, priority=1, table_id=100)
    flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port':4294967293}))
    p.pprint(flow_mod.get_json())
    req = of.PushFlowmod(flow_mod, cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()

def add_flow_mod_ip():
    flow_mod = fm.Flowmod(5, hard_timeout=120)
    match = fm.Match(fm.MatchTypes.ipv4_src, cfg.of_controller_ip)
    match.add_criteria(fm.MatchTypes.eth_type, 2048)
    flow_mod.add_match(match)
    flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port':1}))
    print(flow_mod)
    p.pprint(flow_mod.get_json())
    req = of.PushFlowmod(flow_mod, cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    print(resp)

def query_topology_links():
    req = of.TopologyLinks(cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    adj_mat = resp.get_adj_mat()
    return adj_mat
    # print(resp)

def add_mp_routes():
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, '/home/alexj/programming/research_18/multipath/multipath_seed_files/seed_5678/probabilistic_mean_1_variance_1/', '5678')
    route_adder.install_routes()

def get_sw_desc():
    req = of.SwitchDesc('1016895541745600', cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    print(resp.get_sw_name())

def test_host_mapper():
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    print(hm.map_sw_to_dpid(5))

def add_low_prio_to_all_sws():
    switches = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port).get_response().get_sw_list()
    for sw in switches:
        add_low_prio_flow_mod(sw)

def add_tbl_0_to_all_sws():
    switches = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port).get_response().get_sw_list()
    for sw in switches:
        print(sw)
        flow_mod = fm.Flowmod(sw)
        flow_mod.add_action(fm.Action(fm.ActionTypes.GotoTable, {'table_id' : 100}))
        req = of.PushFlowmod(flow_mod, cfg.of_controller_ip, cfg.of_controller_port)
        req.get_response()

def remove_all_flows():
    switches = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port).get_response().get_sw_list()
    for sw in switches:
        print(sw)
        req = of.RemoveAllFlows(sw, cfg.of_controller_ip, cfg.of_controller_port)
        req.get_response()
    

def mk_readable(adj_mat):
    ret = defaultdict(dict)
    hm = mapper.HostMapper(cfg.dns_server_ip, cfg.of_controller_ip, cfg.of_controller_port)
    for src, v in adj_mat.items():
        print(src)
        src_sw_no = hm.map_dpid_to_sw(str(int(src, 16)))
        for dst, port in v.items():
            dst_sw_no = hm.map_dpid_to_sw(str(int(dst, 16)))
            ret[src_sw_no][dst_sw_no] = port

    return ret

def list_friendly_switch_names():
    req = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port)
    sw_list = req.get_response().get_sw_list()
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    res = {}
    for sw in sw_list:
        friendly = hm.map_dpid_to_sw(str(sw))
        res[sw] = friendly
    
    p.pprint(res)

def sw_to_host_list():
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    return hm.get_switch_to_host_map()

def main():
    # query_flow_stats(5)
    # query_switch_list()
    # add_flow_mod()
    # add_flow_mod_ip()
    adj_mat = query_topology_links()
    pretty = mk_readable(adj_mat)
    p.pprint(pretty)
    # add_mp_routes()
    # get_sw_desc()
    # test_host_mapper()
    # add_low_prio_flow_mod()
    # add_low_prio_to_all_sws()
    # remove_all_flows()
    # add_tbl_0_to_all_sws()
    # list_friendly_switch_names()
    # p.pprint(query_topology_links())
    # p.pprint(sw_to_host_list())
    


if __name__ == '__main__':
    main()