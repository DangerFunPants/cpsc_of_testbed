import multipath_orchestrator as mp
import params as cfg
import host_mapper as hm
import time as t
import datetime as dt
import time as time
from os import mkdir

def bidirectional_ping():
    # bi directional ping.
    host1.connect()
    host5.connect()
    host5_ip = mapper.resolve_hostname('host5')
    host1_ip = mapper.resolve_hostname('host1')
    stdout, _ = host1.exec_command('ping -c4 %s' % host5_ip)
    for line in stdout:
        print(line)
    
    stdout, _ = host5.exec_command('ping -c4 %s' % host1_ip)
    for line in stdout:
        print(line)

def mk_host_defaults(hostname):
    def_host = mp.MPTestHost(hostname, 'alexj', 'cpsc')
    return def_host

def generate_fname():
    curr_time = dt.datetime.now()
    m, d, y = curr_time.month, curr_time.day, curr_time.year
    date_str = ('%d_%d_%d_%d' % (m, d, y, time.time())) 
    return date_str

def test_traffic_transmission(route_adder):

    path_name = generate_fname()
    rx_path = '/home/ubuntu/packet_counts/rx/%s' % path_name
    tx_path = '/home/ubuntu/packet_counts/tx/%s' % path_name
    mkdir(rx_path)
    mkdir(tx_path)

    mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
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

    for (src_host, dst_host) in od_pairs:
        dst_hostname = mapper.map_sw_to_host(dst_host)
        dst_ip = mapper.resolve_hostname(dst_hostname) 
        hosts[src_host].start_client(62500000, 1, 'trunc_norm', 10.0,
            dst_ip, 50000, [0.3,0.5,0.2], src_host, 10)

    input('Press return to stop...')

    for host_id in host_ids:
        hosts[host_id].stop_client()

    for host_id in host_ids:
        hosts[host_id].stop_server()

    for host_id in host_ids:
        hosts[host_id].retrieve_client_files(tx_path)
        hosts[host_id].retrieve_server_files(rx_path)

    for host_id in host_ids:
        hosts[host_id].remove_all_files('%stx' % mp.MPTestHost.COUNT_DIR, 'txt')
        hosts[host_id].remove_all_files('%srx' % mp.MPTestHost.COUNT_DIR, 'p')

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
        
def main():
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, cfg.of_controller_port, cfg.route_path, cfg.seed_no)
    # route_adder.install_routes()
    # time.sleep(5)
    # test_traffic_transmission(route_adder)
    add_then_remove(route_adder)

if __name__ == '__main__':
    main()