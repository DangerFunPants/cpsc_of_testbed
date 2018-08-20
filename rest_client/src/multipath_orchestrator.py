import file_parsing as fp
import of_rest_client as of
import flowmod as fm
import host_mapper as hm
import params as cfg
import paramiko as ssh
import util as util
from functools import reduce
from collections import defaultdict
import threading as thread

# Horrible debugging practice
import pprint as p

class MPRouteAdder:
    
    def __init__( self
                , host
                , port_no
                , defs_dir
                , seed_no ):
        self.host = host
        self.port_no = port_no
        self.defs_dir = defs_dir
        self.seed_no = seed_no
        self.installed_routes = defaultdict(list)

    @staticmethod
    def calculate_dscp_value(flow_num):
        """
        Returns the entire 8 bits of the dscp field (ECN included)
        """
        dscp_val = (flow_num + 1)
        return dscp_val

    def install_routes(self):
        routes = fp.parse_routes(self.defs_dir, self.seed_no)
        # Get a copy of the adjacency matrix
        adj_mat = of.TopologyLinks(self.host, self.port_no).get_response().get_adj_mat()
        p.pprint(adj_mat)
        route_count = 0
        
        for flow_num, vs in enumerate(routes):
            shortest = vs[0]
            # install the default (DSCP 0) route for the shortest path
            # self.install_route(shortest, adj_mat, 0)
            for path_num, route in enumerate(vs):
                dscp_val = MPRouteAdder.calculate_dscp_value(path_num)
                self.install_route(route, adj_mat, dscp_val)
                route_count += 1
        print('Installed %d routes on physical network.' % route_count)

    # Looking back on how this is turning out, it would have been better to inject
    # an actual instnace of some class to interact with the controller, thus indirecting
    # the consumers of that interface from its implementation. Can't really test
    # this route adding code conviniently without an actual controller and network 
    # setup.
    def install_route(self, route, adj_mat, dscp_val):
        pairs = [(src, dst) for (src,dst) in zip(route, route[1:])]
        print(route)
        src_sw = route[0]
        dst_sw = route[-1]

        # Need the IP Address for the hosts.
        mapper = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port) # Could possible query the OS for IP's of dns servers? 
        src_ip = mapper.resolve_hostname(mapper.map_sw_to_host(src_sw))
        dst_ip = mapper.resolve_hostname(mapper.map_sw_to_host(dst_sw))

        for (src, dst) in pairs:
            # Determine output port
            src_dpid = int(mapper.map_sw_to_dpid(src))
            dst_dpid = int(mapper.map_sw_to_dpid(dst))
            out_port = adj_mat[src_dpid][dst_dpid]

            # Determine the actual DPID of the switch
            sw_dpid = mapper.map_sw_to_dpid(src)
            # Construct the correct match criteria. 
            match = fm.Match(fm.MatchTypes.eth_type, 2048) # Math on EthType of IP
            match.add_criteria(fm.MatchTypes.ipv4_src, src_ip)
            match.add_criteria(fm.MatchTypes.ipv4_dst, dst_ip)
            match.add_criteria(fm.MatchTypes.ip_dscp, dscp_val)
            match.add_criteria(fm.MatchTypes.ip_proto, fm.IPProto.UDP.value)
            # match.add_criteria(fm.MatchTypes.udp_dst, 50000)

            # Construct the flowmod.
            flow_mod = fm.Flowmod(sw_dpid, idle_timeout=240, table_id=100, priority=20) # Timeout is only for testing.
            flow_mod.add_match(match)
            flow_mod.add_action(fm.Action(fm.ActionTypes.Output, { 'port' : out_port }))

            # Update the switch.
            req = of.PushFlowmod(flow_mod, self.host, self.port_no)
            resp = req.get_response()
            
            # Save the route so it can be removed later
            self.installed_routes[sw_dpid].append(flow_mod)

    def remove_routes(self):
        for sw_dpid, route_list in self.installed_routes.items():
            for route in route_list:
                req = of.RemoveFlow(sw_dpid, route, 
                    cfg.of_controller_ip, cfg.of_controller_port)
                resp = req.get_response()

    def get_src_dst_pairs(self):
        routes = fp.parse_routes(self.defs_dir, self.seed_no)
        pairs = set()
        for route in routes:
            for path in route:
                pairs.add((path[0], path[-1]))
        return pairs
    
    def get_path_ratios(self):
        path_ratios = fp.parse_flow_defs(self.defs_dir, self.seed_no)
        return path_ratios


class Host:
    """
    Class: Host
    Purpose: Encapsulate parameters and functionality related to individual 
    end hosts. Will allow consumers to run bash commands on the host.
    """

    def __init__( self
                , host_name
                , rem_uname
                , rem_pw
                , ssh_port=22 ):
        self.host_name = host_name
        self.ssh_port = ssh_port
        self.rem_uname = rem_uname
        self.rem_pw = rem_pw
        self.ssh_tunnel = None

        if util.is_ip_addr(host_name):
            self.host_ip = host_name
        else:
            mapper = hm.HostMapper([cfg.man_net_dns_ip], 
                cfg.of_controller_ip, cfg.of_controller_port, domain='management.cpsc.')
            self.host_ip = mapper.resolve_hostname(self.host_name)

    def connect(self):
        self.ssh_tunnel = ssh.SSHClient()
        self.ssh_tunnel.set_missing_host_key_policy(ssh.AutoAddPolicy())
        self.ssh_tunnel.connect(self.host_ip, self.ssh_port, username=self.rem_uname, password=self.rem_pw)
    
    def disconnect(self):
        self.ssh_tunnel.close()
        self.ssh_tunnel = None

    def exec_command(self, command):
        if self.ssh_tunnel:
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
        else:
            self.connect()
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
            self.disconnect()
        return (stdout,stderr)

    def ping(self, remote_host, count=4): 
        ping_command = 'ping -c %d %s' % (count, remote_host)
        stdout, stderr = self.exec_command(ping_command)
        return (stdout, stderr)

class MPTestHost(Host):

    BIN_DIR = '/home/alexj/traffic_generation/' 
    COUNT_DIR = '/home/alexj/packet_counts/'

    def __init__( self
                , host_name
                , rem_uname
                , rem_pw
                , ssh_port = 22 ):
        Host.__init__(self, host_name, rem_uname, rem_pw, ssh_port)
        self._clients = []

    def _add_client(self, client_params):
        self._clients.append(client_params)

    def remove_all_files(self, path, ext):
        comm_str = 'rm -f %s*.%s' % (path, ext)
        self.exec_command(comm_str)
    
    def start_client( self
                    , mu
                    , sigma
                    , traffic_model
                    , dest_ip 
                    , port_no 
                    , k_mat 
                    , host_no 
                    , slice ):

        self.remove_all_files(MPTestHost.COUNT_DIR, 'txt')
        start_comm = '%s/traffic_gen.py' % MPTestHost.BIN_DIR
        k_mat_str = reduce(lambda l, r : str(l) + ' ' + str(r), k_mat)
        args = [ ('-a %s' % dest_ip)
               , ('-p %s' % port_no)
               , ('-k %s' % k_mat_str)
               , ('-t %s' % mu)
               , ('-s %s' % sigma)
               , ('-c %s' % traffic_model)
               , ('-host %s' % host_no)
               , ('-slice %s' % slice)
               , ('-n %s' % 1)
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        comm_str += ' &'
        print(comm_str)
        return self.exec_command(comm_str)

    def stop_client(self):
        command_str = (
            'ps ax | grep -i traffic_gen.py | grep -v grep | awk \'{print $1}\' | xargs -n1 -I {} kill -s SIGINT {}'
        )
        return self.exec_command(command_str)
    
    def start_server(self, host_no):
        self.remove_all_files(MPTestHost.COUNT_DIR, 'p')
        start_comm = '%s/traffic_server.py' % MPTestHost.BIN_DIR
        args = [ ('-host %s' % str(host_no))
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        comm_str += ' &'
        return self.exec_command(comm_str)

    def stop_server(self):
        command_str = (
            'ps ax | grep -i traffic_server.py | grep -v grep | awk \'{print $1}\' | xargs -n1 -I {} kill -s SIGINT {}'
        )
        return self.exec_command(command_str)

    def retrieve_client_files(self, dst_dir):
        local_ip = self.get_local_ip()
        command = 'sshpass -pubuntu scp -o StrictHostKeyChecking=no -r %s*.txt ubuntu@%s:%s' % (self.COUNT_DIR, local_ip, dst_dir)
        print('TX: %s' % command)
        self.exec_command(command)

    def retrieve_server_files(self, dst_dir):
        local_ip = self.get_local_ip()
        command = 'sshpass -pubuntu scp -o StrictHostKeyChecking=no -r %s*.p ubuntu@%s:%s' % (self.COUNT_DIR, local_ip, dst_dir)
        print('RX: %s' % command)
        self.exec_command(command)

    def get_local_ip(self):
        mapper = hm.HostMapper([cfg.man_net_dns_ip], cfg.of_controller_ip,
            cfg.of_controller_port, domain='management.cpsc.')
        local_ip = mapper.resolve_hostname('sdn.cpscopenflow1')
        return local_ip

    def configure_client( self
                        , mu 
                        , sigma
                        , traffic_model
                        , dest_ip
                        , port_no
                        , k_mat
                        , host_no
                        , slice
                        , pkt_len=1066 ):
        client_args = { 'dest_port' : port_no
                      , 'dest_addr': dest_ip
                      , 'prob_mat': k_mat
                      , 'tx_rate': mu
                      , 'variance': sigma
                      , 'traffic_model': traffic_model
                      , 'packet_len': pkt_len
                      , 'src_host': host_no
                      , 'time_slice': slice
                      }
        self._add_client(client_args)

    def start_clients(self):
        command_args = '\"%s\"' % str(self._clients)
        start_comm = '%s/traffic_gen.py' % MPTestHost.BIN_DIR
        comm_str = util.inject_arg_opts(start_comm, [command_args])
        comm_str += ' &'
        print(comm_str)
        return self.exec_command(comm_str)

class MPStatMonitor:

    def __init__( self
                , controller_ip
                , controller_port
                , mon_dpids
                , mon_period=10.0 ):
        self._controller_ip = controller_ip
        self._controller_port = controller_port
        self._rx_stats_list = defaultdict(list)
        self._tx_stats_list = defaultdict(list)
        self._mon_period = mon_period
        self._stop_event = thread.Event()
        self._mon_dpids = mon_dpids
        self._update_stat_lists()

    def _request_port_stats(self, dpid):
        req = of.GetPortStats(dpid, self._controller_ip, self._controller_port)
        resp = req.get_response()
        tx_pkts = resp.get_tx_packets()
        rx_pkts = resp.get_rx_packets()
        return (rx_pkts, tx_pkts)

    def _update_stat_lists(self):
        for dpid in self._mon_dpids:
            rx_pkts, tx_pkts = self._request_port_stats(dpid)
            for port_no, count in tx_pkts.items():
                self._tx_stats_list[(dpid, port_no)].append(count)
            for port_no, count in rx_pkts.items():
                self._rx_stats_list[(dpid, port_no)].append(count)

    def start_monitor(self):
        thread.Timer(self._mon_period, MPStatMonitor._retrieve_stats, [self]).start()

    def stop_monitor(self):
        self._stop_event.set()
        while self._stop_event.isSet():
            pass

    def _retrieve_stats(self):
        self._update_stat_lists()
        if not self._stop_event.isSet():
            self.start_monitor()
        else:
            self._stop_event.clear()

    def retrieve_results(self):
        return (self._rx_stats_list, self._tx_stats_list)
