import multipath_orchestrator as mp
import params as cfg
import host_mapper as hm
import of_rest_client as of
import time as t
import datetime as dt
import time as time
from os import mkdir
import pprint as pp
import util as util
import stats_processor as st_proc
import of_processor as ofp
import pickle as pickle

def mk_host_defaults(hostname):
    def_host = mp.MPTestHost(hostname, 'alexj', 'cpsc')
    return def_host

def generate_fname():
    curr_time = dt.datetime.now()
    m, d, y = curr_time.month, curr_time.day, curr_time.year
    date_str = ('%d_%d_%d_%d' % (m, d, y, time.time())) 
    return date_str

def ping_all():
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    sw_list = of_proc.get_switch_list()
    hosts = {}
    for sw in sw_list:
        sw_num = int(mapper.map_dpid_to_sw_num(sw))
        hostname = mapper.map_sw_to_host(sw_num)
        hosts[sw_num] = mk_host_defaults(hostname)
        hosts[sw_num].connect()
   
    sw_ids = list(map(lambda dpid : mapper.map_dpid_to_sw_num(dpid), sw_list))
    pairs = [ (src, dst) for src in sw_ids for dst in sw_ids if src != dst ]

    for (src, dst) in pairs:
        hostname = mapper.map_sw_to_host(dst)
        rem_ip = mapper.resolve_hostname(hostname)
        fd1, fd2 = hosts[src].ping(rem_ip)
        for ln in fd1:
            print(ln)

def test_traffic_transmission(route_adder, trial_length):

    remove_all_count_files(route_adder)
    mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)
    # Start each trial in a known state
    sw_list = of_proc.get_switch_list()
    for sw in sw_list:
        of_proc.remove_table_flows(sw, 100)
    
    for sw in sw_list:
        of_proc.add_default_route(sw, 100)

    route_adder.install_routes()

    path_name = generate_fname()
    rx_path = '/home/ubuntu/packet_counts/rx/%s' % path_name
    tx_path = '/home/ubuntu/packet_counts/tx/%s' % path_name
    mkdir(rx_path)
    mkdir(tx_path)

    od_pairs = route_adder.get_src_dst_pairs()
    print('ODLen: %d' % len(od_pairs))
    host_ids = set([src for (src, _) in od_pairs]+[dst for (_, dst) in od_pairs])
    print(host_ids)
    hosts = {}
    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = mk_host_defaults(hostname)
        hosts[host_id].connect()
        hosts[host_id].start_server(host_id)

    time.sleep(5)

    path_ratios = route_adder.get_path_ratios()
    pp.pprint(path_ratios)
    for (src_host, dst_host, path_split) in path_ratios:
        dst_hostname = mapper.map_sw_to_host(dst_host)
        dst_ip = mapper.resolve_hostname(dst_hostname)
        hosts[src_host].configure_client(cfg.mu, cfg.sigma, cfg.traffic_model,
            dst_ip, cfg.dst_port, path_split, src_host, cfg.time_slice)


    for s in set([ s for s, _ in od_pairs]):
        hosts[s].start_clients()

    sw_list = of.SwitchList(cfg.of_controller_ip, cfg.of_controller_port).get_response().get_sw_list()
    traffic_mon = mp.MPStatMonitor(cfg.of_controller_ip, cfg.of_controller_port, sw_list)
    traffic_mon.start_monitor()

    time.sleep(trial_length)

    traffic_mon.stop_monitor()

    for host_id in host_ids:
        hosts[host_id].stop_client()

    time.sleep(15)

    for host_id in host_ids:
        hosts[host_id].stop_server()
        
    time.sleep(15)

    for host_id in host_ids:
        hosts[host_id].retrieve_client_files(tx_path)
        hosts[host_id].retrieve_server_files(rx_path)
    
    time.sleep(15)

    for host_id in host_ids:
        hosts[host_id].remove_all_files('%stx' % mp.MPTestHost.COUNT_DIR, 'txt')
        hosts[host_id].remove_all_files('%srx' % mp.MPTestHost.COUNT_DIR, 'p')

    route_adder.remove_routes()
    rx_res, tx_res = traffic_mon.retrieve_results()
    rx_file = './rx_stats.p'
    tx_file = './tx_stats.p'
    pickle.dump(rx_res, open(rx_file, 'wb'))
    pickle.dump(tx_res, open(tx_file, 'wb'))
    record_trial_name(path_name)

def record_trial_name(trial_name):
    with open('./name_hints.txt', 'w') as fd:
        fd.writelines(trial_name)

def test_single_flow_tx():
    mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, '/home/ubuntu/cpsc_of_testbed/route_files/')
    host_ids = [ i for i in range(1, 12) ]
    hosts = {}
    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = mk_host_defaults(hostname)
        hosts[host_id].connect()

def remove_all_count_files(route_adder):
    mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    host_ids = [ i for i in range(1, 12) ]
    hosts = {}
    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = mk_host_defaults(hostname)
        hosts[host_id].connect()
        hosts[host_id].remove_all_files(mp.MPTestHost.COUNT_DIR, 'txt')
        hosts[host_id].remove_all_files(mp.MPTestHost.COUNT_DIR, 'p')

    for host_id in host_ids:
        hosts[host_id].disconnect()

def add_then_remove(route_adder):
    route_adder.install_routes()
    input('Routes have been installed, Press return to remove...')
    route_adder.remove_routes()

def print_route_info(route_adder):
    od_pairs = route_adder.get_src_dst_pairs()
    dups = set(od_pairs)
    print(len(dups))
    for p in od_pairs:
        print(p)
        
def main():
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, cfg.route_path, cfg.seed_no)
    remove_all_count_files(route_adder)
    time.sleep(5)
    test_traffic_transmission(route_adder)

if __name__ == '__main__':
    # main()
    ping_all()
