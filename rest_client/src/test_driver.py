import of_rest_client as of
import flowmod as fm
import pprint as p
import multipath_orchestrator as mp
from util import *
import host_mapper as mapper
import params as cfg
from collections import defaultdict
import time as t
import of_processor as ofp
import pickle as pickle
import stats_processor as stp
import file_parsing as fp
import params as cfg
from sys import argv
import main as trial

def query_flow_stats(dpid):
    req = of.SwitchFlows(dpid, cfg.of_controller_ip, cfg.of_controller_port)
    resp = req.get_response()
    flows = resp.get_flows()
    print(resp)
    p.pprint(flows)

def print_all_flows():
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    req = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port)
    sws = req.get_response().get_sw_list()
    for sw in sws:
        print('***************************************************************')
        print('sw_name: %s' % hm.map_dpid_to_sw(sw))
        print('***************************************************************')

        flow_req = of.SwitchFlows(sw, cfg.of_controller_ip, cfg.of_controller_port)
        resp = flow_req.get_response()
        p.pprint(resp.get_flows())


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
    hm = mapper.HostMapper(cfg.dns_server_ip, cfg.of_controller_ip, cfg.of_controller_port)
    sw_dpid = hm.map_sw_to_dpid(5)
    flow_mod = fm.Flowmod(sw_dpid, hard_timeout=120, priority=20, table_id=100)
    match = fm.Match(fm.MatchTypes.ipv4_src, '10.0.15.2')
    match.add_criteria(fm.MatchTypes.eth_type, 2048)
    flow_mod.add_match(match)
    flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port':23}))
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

def add_mp_routes():
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, cfg.route_path, cfg.seed_no)
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
        src_sw_no = hm.map_dpid_to_sw(src)
        for dst, port in v.items():
            dst_sw_no = hm.map_dpid_to_sw(dst)
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

def test_command_execution():
   th = mp.MPTestHost('www.google.ca', 'uname', 'pw')
   v = th.start_client(131072, 131, 'gamma', 10, '10.0.0.5', 50000, '[1, 2, 3]', 1)
   v2 = th.start_server(1)
   print(v)
   print(v2)
   
def switch_ssh_test():
    switch = mp.OFSwitchHost('switch-1')
    fd1, fd2 = switch.list_switches()
    for line in fd1:
        print(line)
    for line in fd2:
        print(line)

def stat_mon_test():
    switches = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port).get_response().get_sw_list()
    monitor = mp.MPStatMonitor(cfg.of_controller_ip, cfg.of_controller_port, switches, mon_period=5.0)
    monitor.start_monitor()
    t.sleep(30)
    monitor.stop_monitor()
    p.pprint(monitor.retrieve_results())

def new_of_api_test():
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    for dpid in of_proc.get_switch_list():
        desc = of_proc.get_switch_desc(dpid)
        print('%s -> %s' % (dpid, desc.get_sw_name()))

    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    p.pprint(mk_pretty_sw_dict(of_proc.get_topo_links().get_adj_mat(), hm, lambda k : k, lambda n, k : n))

def read_trial_name(file_path):
    with open(file_path, 'r') as fd:
        line = fd.readline()
    return line.strip()

def test_stats_processor():
    trial_name = read_trial_name('./name_hints.txt')
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    tx_file = './tx_stats.p'
    stats = pickle.load(open(tx_file, 'rb'))
    pretty_stats = mk_pretty_sw_dict(stats, hm, lambda k : k[0], lambda n, k : (n, k[1]))
    p.pprint(pretty_stats)
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    st_dict = st_proc.calc_link_util(stats, 1066, 10.0, units=stp.Units.MegaBitsPerSecond)
    p.pprint(st_dict)
    p.pprint(st_proc.calc_loss_rates(trial_name))

def test_pkt_loss_analysis():
    trial_name = '8_7_2018_1533690234'
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    st_proc.calc_loss_rates(trial_name)

def remove_all_tbl_100_flows():
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    sw_list = of_proc.get_switch_list()
    for sw in sw_list:
        of_proc.remove_table_flows(sw, 100)

def analyze_kriskoll_topology():
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    ports = eval(open('./kriskoll_res.txt', 'r').read())
    pretty = mk_pretty_sw_dict(ports, hm, lambda k : k, lambda n, k : n)
    p.pprint(pretty)

def test_file_parsing():
    paths = fp.parse_flow_defs(cfg.route_path, cfg.seed_no)    
    p.pprint(paths)

def pprint_mst_topo():
    val = {1126987699366720: set([24, 19, 21]), 1579845495207200: set([16, 18, 20, 14]), 1016895541745600: set([17, 15]), 845512722656064: set([13, 15]), 1016895541785888: set([17, 13, 15]), 1408462676077376: set([16, 18, 20, 14]), 1016895541798336: set([17, 12, 13, 15]), 1579845495166912: set([18, 20, 14]), 1298370518496544: set([24, 19, 21]), 1298370518456256: set([24, 23]), 1298370518508992: set([19, 23])}
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    p.pprint(mk_pretty_sw_dict(val, hm, lambda k : k, lambda n, k : n))

def port_stats(sw_id):
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    dpid = hm.map_sw_to_dpid(int(sw_id))
    p.pprint(of_proc.get_port_stats(dpid).get_rx_packets())

def main():
    # query_flow_stats(5)
    # query_switch_list()
    # add_flow_mod()
    # add_flow_mod_ip()
    adj_mat = query_topology_links()
    p.pprint(adj_mat)
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
    # test_command_execution()
    # print_all_flows()
    # add_flow_mod_ip()
    # remove_all_tbl_100_flows()
    # add_low_prio_to_all_sws()
    # hm = mapper.HostMapper(cfg.dns_server_ip, cfg.of_controller_ip, cfg.of_controller_port)
    # for sw in [8, 9, 5]:
    #     print('Switch with id: %s' % sw)
    #     print('***************************************************************')
    #     query_flow_stats(int(hm.map_sw_to_dpid(sw)))
    # switch_ssh_test()
    # stat_mon_test()
    # new_of_api_test()
    # test_stats_processor()
    # remove_all_tbl_100_flows()
    # add_low_prio_to_all_sws()
    # print_all_flows()
    # analyze_kriskoll_topology()
    # test_file_parsing()
    # test_pkt_loss_analysis()
    # pprint_mst_topo()

    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)


    if argv[1] == 'remove':
        remove_all_tbl_100_flows()
        add_low_prio_to_all_sws()
    elif argv[1] == 'flows':
        if len(argv) == 2:
            print_all_flows()
        elif len(argv) == 3:
            sw_dpid = hm.map_sw_to_dpid(int(argv[2]))
            flows = of_proc.get_switch_flows(int(sw_dpid))
            p.pprint(flows.get_flows())
    elif argv[1] == 'mst':
        pprint_mst_topo()
    elif argv[1] == 'start':
        route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, cfg.route_path, cfg.seed_no)
        trial.test_traffic_transmission(route_adder)
    elif argv[1] == 'ports':
        port_stats(argv[2])        
    elif argv[1] == 'rem_sw':
        sw_dpid = hm.map_sw_to_dpid(int(argv[2]))
        of_proc.remove_table_flows(sw_dpid, 100)
        of_proc.add_default_route(sw_dpid, 100)
    elif argv[1] == 'stats':
        test_stats_processor()
    elif argv[1] == 'add':
        add_flow_mod_ip()
    elif argv[1] == 'dpid':
        list_friendly_switch_names()

    
    
    


if __name__ == '__main__':
    main()
