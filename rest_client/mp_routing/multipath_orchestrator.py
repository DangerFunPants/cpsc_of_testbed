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

from rest_client import nw_control 

# Horrible debugging practice
import pprint as p

class MPRouteAdder:
    
    def __init__( self
                , of_proc
                , mapper
                , route_provider ):
        self._route_provider = route_provider
        self.installed_routes = defaultdict(list)
        self.of_proc = of_proc
        self._mapper = mapper

    @staticmethod
    def calculate_dscp_value(flow_num):
        """
        Returns the entire 8 bits of the dscp field (ECN included)
        """
        dscp_val = (flow_num + 1)
        return dscp_val

    def install_routes(self):
        routes = self._route_provider.get_routes()
        # Get a copy of the adjacency matrix
        adj_mat = self.of_proc.get_topo_links().get_adj_mat()
        route_count = 0
        
        for path_id, route in routes:
            dscp_val = MPRouteAdder.calculate_dscp_value(path_id)
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
        src_sw = route[0]
        dst_sw = route[-1]
        #print('multipath_orchestrator:')
        print((src_sw, dst_sw))
        # Need the IP Address for the hosts.
        src_ip = self._mapper.resolve_hostname(self._mapper.map_sw_to_host(src_sw))
        dst_ip = self._mapper.resolve_hostname(self._mapper.map_sw_to_host(dst_sw))

        for (src, dst) in pairs:
            # Determine output port
            src_dpid = int(self._mapper.map_sw_to_dpid(src))
            dst_dpid = int(self._mapper.map_sw_to_dpid(dst))
            try:
                out_port = adj_mat[src_dpid][dst_dpid]
            except KeyError:
                print('Found no link: %s -> %s' % (src, dst))
                continue

            # Determine the actual DPID of the switch
            sw_dpid = self._mapper.map_sw_to_dpid(src)
            # Construct the correct match criteria. 
            match = fm.Match(fm.MatchTypes.eth_type, 2048) # Math on EthType of IP
            match.add_criteria(fm.MatchTypes.ipv4_src, src_ip)
            match.add_criteria(fm.MatchTypes.ipv4_dst, dst_ip)
            match.add_criteria(fm.MatchTypes.ip_dscp, dscp_val)
            match.add_criteria(fm.MatchTypes.ip_proto, fm.IPProto.UDP.value)
            # TODO: Add filter criteria based on L4 Address (Port number)

            # Construct the flowmod.
            flow_mod = fm.Flowmod(src_dpid, idle_timeout=240, table_id=100, priority=20) # Timeout is only for testing.
            flow_mod.add_match(match)
            flow_mod.add_action(fm.Action(fm.ActionTypes.Output, { 'port' : out_port }))

            # Update the switch.
            self.of_proc.push_flow_mod(src_dpid, flow_mod)
            
            # Save the route so it can be removed later
            self.installed_routes[sw_dpid].append(flow_mod)

    def remove_routes(self):
        for sw_dpid, route_list in self.installed_routes.items():
            for route in route_list:
                self.of_proc.remove_flow(sw_dpid, route)

    def get_src_dst_pairs(self):
        routes = self._route_provider.get_routes()
        pairs = set()
        for _, path in routes:
            pairs.add((path[0], path[-1]))
        return pairs
    
    def get_path_ratios(self):
        path_ratios = self._route_provider.get_flow_defs()
        return path_ratios

    def get_tx_rates(self):
        tx_rates = self._route_provider.get_tx_rates()
        return tx_rates


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
