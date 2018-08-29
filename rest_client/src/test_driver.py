#!/usr/bin/env python3

# System Imports
import argparse as ap
import pprint as p
import sys
import pickle
from collections import defaultdict
import time as t

# PyPlot Library
import matplotlib.pyplot as plt

# Local Imports
import of_rest_client as of
import flowmod as fm
import multipath_orchestrator as mp
from util import *
import host_mapper as mapper
import params as cfg
import of_processor as ofp
import stats_processor as stp
import file_parsing as fp
import params as cfg
import main as trial
import topology as vis

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
        src_sw_no = hm.map_dpid_to_sw(src)
        for dst, port in v.items():
            dst_sw_no = hm.map_dpid_to_sw(dst)
            ret[src_sw_no][dst_sw_no] = port

    return ret

def list_friendly_switch_names(hm, of_proc):
    sw_list = of_proc.get_switch_list()
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

def test_stats_processor(hm, of_proc):
    trial_name = read_trial_name('./name_hints.txt')
    tx_file = './tx_stats.p'
    rx_file = './rx_stats.p'
    stats = pickle.load(open(tx_file, 'rb'))
    rx_stats = pickle.load(open(rx_file, 'rb'))
    st_proc = stp.StatsProcessor(hm, of_proc)
    p.pprint(stats)
    st_dict = st_proc.calc_link_util(stats, cfg.pkt_size, cfg.sample_freq, units=stp.Units.MegaBitsPerSecond)
    ingress_flows_dict = st_proc.calc_ingress_util(rx_stats, cfg.pkt_size, cfg.sample_freq, units=stp.Units.MegaBitsPerSecond)
    egress_flows_dict = st_proc.calc_ingress_util(stats, cfg.pkt_size, cfg.sample_freq, units=stp.Units.MegaBitsPerSecond)
    print('*******************************************************************')
    print('CORE LINK UTILIZATION')
    p.pprint(st_dict)

    print('*******************************************************************')
    print('HOST UPLINK UTILIZATION')
    p.pprint(ingress_flows_dict)
    
    print('*******************************************************************')
    print('HOST EGRESS UTILIZATION')
    p.pprint(egress_flows_dict)

    print('*******************************************************************')
    print('LOSS RATES')
    p.pprint(st_proc.calc_loss_rates(trial_name))

    print('*******************************************************************')
    print('GOODPUT FOR FLOWS')
    p.pprint(st_proc.calc_flow_rate(trial_name, cfg.pkt_size, cfg.sample_freq, cfg.trial_length))
    print('*******************************************************************')

def calc_stats_list():
    trial_name = read_trial_name('./name_hints.txt')
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    tx_file = './tx_stats.p'
    rx_file = './rx_stats.p'
    stats = pickle.load(open(tx_file, 'rb'))
    rx_stats = pickle.load(open(rx_file, 'rb'))
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    st_dict = st_proc.calc_link_util_per_t(stats, cfg.pkt_size, cfg.sample_freq, units=stp.Units.MegaBitsPerSecond)
    p.pprint(st_dict)

def print_local_loss():
    st_proc = stp.StatsProcessor(None, None, '/home/alexj/packet_counts/')
    trial_name = ''
    print('LOSS RATES')
    p.pprint(st_proc.calc_loss_rates(trial_name))
    print('*******************************************************************')
    print('GOODPUT FOR FLOWS')
    p.pprint(st_proc.calc_flow_rate(trial_name, cfg.pkt_size, cfg.sample_freq, cfg.trial_length))
    print('*******************************************************************')


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

def port_stats(sw_id, hm, of_proc):
    dpid = hm.map_sw_to_dpid(int(sw_id))
    p.pprint(of_proc.get_port_stats(dpid).get_rx_packets())

def print_all_port_stats(hm, of_proc):
    sw_list = of_proc.get_switch_list()
    for sw in sw_list:
        p.pprint(of_proc.get_port_stats(sw).get_rx_packets())

def plot_test():
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    grapher = stp.Grapher()

    trial_name = read_trial_name('./name_hints.txt')
    tx_file = './tx_stats.p'
    rx_file = './rx_stats.p'
    tx_stats = pickle.load(open(tx_file, 'rb'))
    rx_stats = pickle.load(open(rx_file, 'rb'))

    stats_list = st_proc.calc_link_util_per_t(tx_stats, cfg.pkt_size, cfg.time_slice, stp.Units.MegaBitsPerSecond)
    stats_avg = st_proc.calc_link_util(tx_stats, cfg.pkt_size, cfg.time_slice, stp.Units.MegaBitsPerSecond)
    stats_loss = st_proc.calc_loss_rates(read_trial_name('./name_hints.txt'))
    stats_uplink = st_proc.calc_ingress_util_per_t(rx_stats, cfg.pkt_size, cfg.time_slice, stp.Units.MegaBitsPerSecond)
    stats_tput = st_proc.calc_flow_rate(trial_name, cfg.pkt_size, cfg.sample_freq, cfg.trial_length)

    grapher.graph_util_over_time(stats_list, 'util_per_ts', show_plot=True)

    fig, ax = plt.subplots(1, 1)
    grapher.graph_loss_cdf(ax, stats_loss, 'loss_plot')
    fig.savefig('loss_plot.png')


    grapher.graph_util_over_time(stats_uplink, 'uplink_ports')


def gen_boxplot(input_files):
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    grapher = stp.Grapher()

    fig, ax = plt.subplots(1, 1)
    stats_avg = []
    for i, f in enumerate(input_files):
        stat_path = f + '/tx_stats.p'
        tx_stats = pickle.load(open(stat_path, 'rb')) 
        link_util = st_proc.calc_link_util(tx_stats, cfg.pkt_size, cfg.time_slice, stp.Units.MegaBitsPerSecond)
        flat = [ util for v in link_util.values() for util in v.values() ]
        stats_avg.append(flat)
    grapher.graph_timeframes(ax, stats_avg, input_files)
    plt.show()

    fig, ax = plt.subplots(1, 1)
    stats_avg = []
    for i, f in enumerate(input_files):
        stat_path = f + '/tx_stats.p'
        tx_stats = pickle.load(open(stat_path, 'rb')) 
        trial_name = read_trial_name(f + '/name_hints.txt')
        flow_rate = st_proc.calc_flow_rate(trial_name, cfg.pkt_size, cfg.sample_freq, cfg.trial_length)
        flat = [ rate for v in flow_rate.values() for u in v.values() for rate in u.values() ]
        stats_avg.append(flat)
    
    grapher.graph_timeframes(ax, stats_avg, input_files)
    plt.show()

def gen_lossplot(input_files):
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    st_proc = stp.StatsProcessor(hm, of_proc)
    grapher = stp.Grapher()

    fig, ax = plt.subplots(1, 1)
    stats_avg = []
    for i, f in enumerate(input_files):
        trial_name = f + '/name_hints.txt'
        loss_stats = st_proc.calc_loss_rates(read_trial_name(trial_name))
        grapher.graph_loss_cdf(ax, loss_stats, f)
    legend = ax.legend(loc='bottom right', shadow=True, fontsize='medium')
    plt.show()

def test_install(route_adder):
    t_i = t.perf_counter()
    route_adder.install_routes()
    t_f = t.perf_counter()
    print('Installing routes took: %f seconds' % (t_f - t_i))

def show_adj_mat(hm, of_proc):
    adj_mat = of_proc.get_topo_links()
    p.pprint(mk_readable(adj_mat.get_adj_mat()))

def remove_handler(args, hm, of_proc):
    if args.switch:
        sw_dpid = hm.map_sw_to_dpid(args.switch)
        of_proc.remove_table_flows(sw_dpid, 100)
        of_proc.add_default_route(sw_dpid, 100)
    else:
        remove_all_tbl_100_flows()
        add_low_prio_to_all_sws()

def flows_handler(args, hm, of_proc):
    if args.switch:
        sw_dpid = hm.map_sw_to_dpid(args.switch)
        flows = of_proc.get_switch_flows(int(sw_dpid))
        p.pprint(flows.get_flows())
    else:
        print_all_flows()

def mst_handler(args, hm, of_proc):
    pprint_mst_topo()

def start_handler(args, hm, of_proc):
    trial_type = args.trial_type.lower()
    route_adder = None
    if trial_type == 'link':
        route_input = args.file_name
        seed_no = args.seed_no
        route_path = cfg.link_route_path(seed_no) + route_input + '/'
        route_provider = fp.MPTestFileParser(route_path, seed_no)
        route_adder = mp.MPRouteAdder(of_proc, hm, route_provider)
    elif trial_type == 'node':
        route_input = args.file_name
        seed_no = args.seed_no
        route_path = cfg.node_route_path + route_input + '/' + 'seed_%s' % seed_no + '/'
        route_provider = fp.NETestFileParser(route_path, seed_no)
        route_adder = mp.MPRouteAdder(of_proc, hm, route_provider)
    else:
        print('Invalid trial type: %s. Valid types are: [ link | node ]' % trial_type)
        sys.exit(0)
    trial.test_traffic_transmission(route_adder, args.time)

def ports_handler(args, hm, of_proc):
    if args.switch:
        port_stats(args.switch, hm, of_proc)
    else:
        print_all_port_stats(hm, of_proc)

def stats_handler(args, hm, of_proc):
    test_stats_processor(hm, of_proc)

def names_handler(args, hm, of_proc):
    list_friendly_switch_names(hm, of_proc)
    pass

def graph_handler(args, hm, of_proc):
    if args.type == 'boxplot':
        gen_boxplot(args.file_list)
    elif args.type == 'lossplot':
        gen_lossplot(args.file_list)
    elif args.type == 'topology':
        vis.draw_topology()

def main():
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    hm = mapper.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)

    arg_parser = build_arg_parser()
    args = arg_parser.parse_args()
    args.func(args, hm, of_proc)

def build_arg_parser():
    parser = ap.ArgumentParser()
    subparsers = parser.add_subparsers()

    # remove all flows
    parser_remove = subparsers.add_parser('remove')
    parser_remove.add_argument('--switch', type=int)
    parser_remove.set_defaults(func=remove_handler)

    # print all flows
    parser_flows = subparsers.add_parser('flows')
    parser_flows.add_argument('--switch', type=int)
    parser_flows.set_defaults(func=flows_handler)

    # print the minimum spanning tree
    parser_mst = subparsers.add_parser('mst')
    parser_mst.set_defaults(func=mst_handler)

    # Start a link embedding trial
    parser_start = subparsers.add_parser('start')
    parser_start.add_argument('trial_type', type=str)
    parser_start.add_argument('file_name', type=str)
    parser_start.add_argument('seed_no', type=str)
    parser_start.add_argument('--time', type=int, nargs='?', const=60)
    parser_start.set_defaults(func=start_handler)

    # Display switch port info.
    parser_ports = subparsers.add_parser('ports')
    parser_ports.add_argument('--switch', type=int)
    parser_ports.set_defaults(func=ports_handler)

    # Print statistics in the current working directory
    parser_stats = subparsers.add_parser('stats')
    parser_stats.set_defaults(func=stats_handler)

    # Print the list of switches currently in the network
    parser_names = subparsers.add_parser('names')
    parser_names.set_defaults(func=names_handler)

    # Generate a graph
    parser_graph = subparsers.add_parser('graph')
    parser_graph.add_argument('file_list', nargs='?', const='prob_mean_1_sigma_1.0')
    parser_graph.add_argument('--type', type=str, required = True)
    parser_graph.set_defaults(func=graph_handler)
    
    return parser

if __name__ == '__main__':
    main()

