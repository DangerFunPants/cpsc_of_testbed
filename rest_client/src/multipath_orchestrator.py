import file_parsing as fp
import of_rest_client as of
import flowmod as fm
import host_mapper as hm
import params as cfg
import paramiko as ssh_lib

class MPRouteAdder:
    
    def __init__( self
                , host
                , port
                , defs_dir
                , seed_no ):
        self.host = host
        self.port = port
        self.defs_dir = defs_dir

    def install_routes(self):
        routes = fp.parse_routes(self.defs_dir, seed_no)
        # Get a copy of the adjacency matrix
        adj_mat = of.TopologyLinks(self.host, self.port_no).get_response().get_adj_mat()
        for i, route in enumerate(routes):
            self.install_route(route, adj_mat)

    # Looking back on how this is turning out, it would have been better to inject
    # an actual instnace of some class to interact with the controller, thus indirecting
    # the consumers of that interface from its implementation. Can't really test
    # this route adding code conviniently without an actual controller and network 
    # setup.
    def install_route(self, route, adj_mat, flow_num):
        pairs = [(src, dst) for (src,dst) in zip(route, route[1:])]

        src_sw = route[0]
        dst_sw = route[-1]

        # Need the IP Address for the hosts.
        hm = hm.HostMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port) # Could possible query the OS for IP's of dns servers? 
        src_ip = hm.resolve_hostname(hm.map_sw_to_host(src_sw))
        dst_ip = hm.resolve_hostname(hm.map_sw_to_host(dst_sw))

        for (src, dst) in pairs:
            # Determine output port
            out_port = adj_mat[src][dst]

            # Determine the actual DPID of the switch
            sw_dpid = hm.map_sw_to_dpid(src)

            # Construct the correct match criteria. 
            match = fm.Match(fm.MatchTypes.eth_type, 2048) # Math on EthType of IP
            match.add_criteria(fm.MatchTypes.ipv4_src, src_ip)
            match.add_criteria(fm.MatchTypes.ipv4_dst, dst_ip)

            # Construct the flowmod.
            flow_mod = fm.Flowmod(sw_dpid, hard_timeout=120) # Timeout is only for testing.
            flow_mod.add_match(match)
            flow_mod.add_action(fm.Action(fm.ActionTypes.Output, out_port))

            # Update the switch.
            req = of.PushFlowmod(flow_mod, self.host, self.port)
            resp = req.get_response()

class Host:
    """
    Class: Host
    Purpose: Allow consumers to execute commands on remote hosts.
    """

    def __init__(self, host_name):
        self.host_name = host_name
        mapper = hm.HostMapper([cfg.man_net_dns_ip],
                cfg.of_controller_ip, cfg.of_controller_port)
        self.host_ip = mapper.resolve_hostname(self.host_name)

    def mk_ssh_client(self):
        conn = ssh_lib.SSHClient()
        conn.connect(self.host_ip, username=cfg.host_uname,
                password=cfg.host_pw)
        return conn

    def exec_command(self, command_str):
        conn = self.mk_ssh_client()
        conn.exec_command(command_str)


