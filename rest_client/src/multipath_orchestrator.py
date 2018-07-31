import file_parsing as fp
import of_rest_client as of
import flowmod as fm
import host_mapper as hm
import params as cfg
import paramiko as ssh
import util as util
from functools import reduce

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

    @staticmethod
    def calculate_dscp_value(flow_num):
        """
        Returns the entire 8 bits of the dscp field (ECN included)
        """
        dscp_val = (flow_num + 1) * 4
        return dscp_val

    def install_routes(self):
        routes = fp.parse_routes(self.defs_dir, self.seed_no)
        # Get a copy of the adjacency matrix
        adj_mat = of.TopologyLinks(self.host, self.port_no).get_response().get_adj_mat()
        p.pprint(adj_mat)
        route_count = 0
        for flow_num, vs in enumerate(routes):
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
            print((src, dst))
            # Determine output port
            src_dpid = int(mapper.map_sw_to_dpid(src))
            dst_dpid = int(mapper.map_sw_to_dpid(dst))
            print((src_dpid, dst_dpid))
            out_port = adj_mat[src_dpid][dst_dpid]
            print(out_port)

            # Determine the actual DPID of the switch
            sw_dpid = mapper.map_sw_to_dpid(src)

            # Construct the correct match criteria. 
            match = fm.Match(fm.MatchTypes.eth_type, 2048) # Math on EthType of IP
            match.add_criteria(fm.MatchTypes.ipv4_src, src_ip)
            match.add_criteria(fm.MatchTypes.ipv4_dst, dst_ip)
            match.add_criteria(fm.MatchTypes.ip_dscp, dscp_val)

            # Construct the flowmod.
            flow_mod = fm.Flowmod(sw_dpid, hard_timeout=60, table_id=100, priority=20) # Timeout is only for testing.
            flow_mod.add_match(match)
            flow_mod.add_action(fm.Action(fm.ActionTypes.Output, { 'port' : out_port }))

            # Update the switch.
            req = of.PushFlowmod(flow_mod, self.host, self.port_no)
            resp = req.get_response()

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
                cfg.of_controller_ip, cfg.of_controller_port)
            self.host_ip = mapper.resolve_hostname(self.host_name)

    def connect():
        self.ssh_tunnel = ssh.SSHClient()
        self.ssh_tunnel.set_missing_host_key_policy(ssh.AutoAddPolicy())
        self.ssh_tunnel.connect(self.host_ip, self.ssh_port)
    
    def disconnect():
        self.ssh_tunnel.close()
        self.ssh_tunnel = None

    def exec_command(command):
        if self.ssh_tunnel:
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
        else:
            self.connect()
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
            self.disconnect()
        return (stdout,stderr)

class MPTestHost(Host):

    BIN_DIR = '/home/alexj/traffic_generation/' 

    def __init__( self
                , host_name
                , rem_uname
                , rem_pw
                , ssh_port = 22 ):
        Host.__init__(self, host_name, rem_pw, ssh_port)
    
    def start_client( self
                    , mu
                    , sigma
                    , traffic_model
                    , time_slice 
                    , dest_ip 
                    , port_no 
                    , k_mat 
                    , host_no ):

        start_comm = '%s/traffic_gen.py' % MPTestHost.BIN_DIR
        args = [ ('-a %s' % dest_ip)
               , ('-p %s' % port_no)
               , ('-k %s' % k_mat)
               , ('-t %s' % mu)
               , ('-s %s' % sigma)
               , ('-c %s' % traffic_model)
               , ('-host %s' % host_no)
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        return comm_str
    
    def start_server(self, host_no):
        start_comm = '%s/traffic_server.py' % MPTestHost.BIN_DIR
        args = [ ('-host %s' % host_no) 
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        return comm_str

    