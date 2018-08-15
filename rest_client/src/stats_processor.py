import statistics as stat
from collections import defaultdict
from enum import Enum
import glob as glob
import os.path as os_path
import pickle as pick
import pprint as pp

class Units(Enum):
    PacketsPerSecond = 0
    MegaBitsPerSecond = 1
    BitsPerSecond = 2
    BytesPerSecond = 3
    MegaBytesPerSecond = 4

class StatsProcessor:
    def __init__( self
                , mapper
                , of_proc
                , base_path='/home/ubuntu/packet_counts/'
                ):
        self._mapper = mapper
        self._of_proc = of_proc
        self.base_path = base_path

    def _get_link(self, src_dpid, port_no):
        topo = self._of_proc.get_topo_links().get_adj_mat()
        next_hop = list(filter(lambda t : t[1] == port_no, topo[src_dpid].items()))
        if next_hop:
            return (src_dpid, next_hop[0][0])
        else:
            raise ValueError('Port %d on %d is not in the core of the network'
                % (port_no, src_dpid))

    def _get_friendly_link(self, src_dpid, port_no):
        link = self._get_link(src_dpid, port_no)
        names = map(self._mapper.map_dpid_to_sw, link)
        return names

    def _is_core_port(self, dpid, port_no):
        try:
            self._get_link(dpid, port_no)
        except ValueError:
            return False
        return True

    def _is_host_port(self, dpid, port_no):
        return not self._is_core_port(dpid, port_no)

    def _calc_link_util_pps(self, stats_dict):
        # stats_dict :: (sw_dpid, egress_port) -> [pkt_counts]
        timeframes = self._compute_timeframes(stats_dict)
        link_utils = defaultdict(dict)
        for (sw_dpid, egress_port), count_list in timeframes.items():
            try:
                src_nm, dst_nm = self._get_friendly_link(sw_dpid, egress_port)
            except ValueError:
                continue
            avg_util = stat.mean(count_list)
            link_utils[src_nm][dst_nm] = avg_util
        return link_utils
    
    def _calc_link_util_pps_t(self, stats_dict):
        timeframes = self._compute_timeframes(stats_dict)
        link_utils = defaultdict(lambda : defaultdict(list))
        for (sw_dpid, egress_port), count_list in timeframes.items():
            try:
                src_nm, dst_nm = self._get_friendly_link(sw_dpid, egress_port)
            except ValueError:
                continue
            link_utils[src_nm][dst_nm] = count_list
        return link_utils


    def _calc_uplink_port_util_pps(self, stats_dict):
        timeframes = self._compute_timeframes(stats_dict)
        link_utils = defaultdict(dict)
        for (sw_dpid, egress_port), count_list in timeframes.items():
            if self._is_host_port(sw_dpid, egress_port):
                sw_name = self._mapper.map_dpid_to_sw(sw_dpid)
                link_utils[sw_name][egress_port] = stat.mean(count_list)
        return link_utils

    def _compute_timeframes(self, results_store):
        return { k : list(map(lambda t : t[1] - t[0], zip(v, v[1:]))) for k, v in results_store.items() }

    def _convert_stats(self, stats_dict, conv_fn):
        ret = defaultdict(dict)
        for src_sw, v in stats_dict.items():
            for dst_sw, count in v.items():
                ret[src_sw][dst_sw] = conv_fn(count)
        return ret

    def _convert_stats_list(self, stats_dict, conv_fn):
        ret = defaultdict(dict)
        for src_sw, v in stats_dict.items():
            for dst_sw, count_list in v.items():
                ret[src_sw][dst_sw] = list(map(conv_fn, count_list))
        return ret

    def _build_conv_fn(self, pkt_size, time_frame, units=Units.PacketsPerSecond):
        if units == Units.PacketsPerSecond:
            conv_fn = lambda pkts : (pkts / float(time_frame))
        elif units == Units.BitsPerSecond:
            conv_fn = lambda pkts : ((pkts * pkt_size * 8) / float(time_frame))
        elif units == Units.MegaBitsPerSecond:
            conv_fn = lambda pkts : (((pkts * pkt_size * 8) / float(10**6)) / float(time_frame))
        elif units == Units.BytesPerSecond:
            conv_fn = lambda pkts : ((pkts * 1066) / float(time_frame))
        elif units == Units.MegaBytesPerSecond:
            conv_fn = lambda pkts : (((pkts * 1066) / float(10**6)) / float(time_frame))
        return conv_fn

    def _calc_link_util(self, pps_stats, pkt_size, time_frame, units=Units.PacketsPerSecond):
        conv_fn = self._build_conv_fn(pkt_size, time_frame, units)
        return self._convert_stats(pps_stats, conv_fn)
    
    def _calc_link_util_list(self, pps_stats, pkt_size, time_frame, units=Units.PacketsPerSecond):
        conf_fn = self._build_conv_fn(pkt_size, time_frame, units)
        return self._convert_stats_list(pps_stats, conf_fn)

    def calc_link_util(self, stats_dict, pkt_size, time_frame, units=Units.PacketsPerSecond):
        pps_stats = self._calc_link_util_pps(stats_dict)
        stats = self._calc_link_util(pps_stats, pkt_size, time_frame, units)
        return stats
    
    def calc_link_util_t(self, stats_dict, pkt_size, time_frame, units=Units.PacketsPerSecond):
        pps_stats = self._calc_link_util_pps_t(stats_dict)
        stats = self._calc_link_util_list(pps_stats, pkt_size, time_frame, units)
        return stats

    def calc_ingress_util(self, stats_dict, pkt_size, time_frame, units=Units.PacketsPerSecond):
        pps_stats = self._calc_uplink_port_util_pps(stats_dict)
        stats = self._calc_link_util(pps_stats, pkt_size, time_frame, units)
        return stats

    def _get_src_dst_pair(self, file_name):
        base = os_path.basename(file_name)
        toks, _ = os_path.splitext(base)
        toks = toks.split('-')
        src_host, dst_host = int(toks[0].split('_')[1]), int(toks[1])
        return (src_host, dst_host)

    def _mk_tx_dict(self, tx_files):
        tx_dict = defaultdict(dict)
        for f in tx_files:
            with open(f, 'r') as fd:
                pkts = int(fd.readlines()[0])
                src_host, dst_host = self._get_src_dst_pair(f)
                dst_ip = '10.0.0.%d' % dst_host
                dst_hname = self._mapper.reverse_lookup(dst_ip)
                src_hname = self._mapper.qualify_host_domain(self._mapper.map_sw_to_host(src_host))
                tx_dict[src_hname][dst_hname] = pkts
        return tx_dict

    def _mk_rx_dict(self, rx_files):
        rx_dict = defaultdict(dict)
        for f in rx_files:
            with open(f, 'rb') as fd:
                infos = pick.load(fd)
                for (src_ip, _), pkt_count in infos.items():
                    base, _ = os_path.splitext(os_path.basename(f))
                    rx_er = base.split('_')[1]
                    rx_host = self._mapper.qualify_host_domain(self._mapper.map_sw_to_host(rx_er))
                    hostname = self._mapper.reverse_lookup(src_ip)
                    rx_dict[rx_host][hostname] = pkt_count
        return rx_dict
    
    def calc_pkt_loss(self, tx_pkts, rx_pkts):
        pkt_loss = (tx_pkts - rx_pkts) / float(tx_pkts)
        return pkt_loss
    
    def _mk_loss_dict(self, tx_dict, rx_dict):
        loss_dict = defaultdict(dict)
        for src_host, flows in tx_dict.items():
            for dst_host, tx_pkts in flows.items():
                print('SRC: %s, DST: %s' % (src_host, dst_host))
                try:
                    rx_pkts = rx_dict[dst_host][src_host]
                except KeyError:
                    print('ERROR: RxDict lookup failed. ignoring flow %s -> %s' % 
                        (src_host, dst_host))
                    continue
                loss_dict[src_host][dst_host] = self.calc_pkt_loss(tx_pkts, rx_pkts)
        return loss_dict
    
    def calc_loss_rates(self, trial_name):
        """
        This method makes some irritating assumptions about file paths
        to the pkl and txt files containing the packet drop rate
        statistics
        """
        base_path = self.base_path
        tx_path = '%s%s%s/*.txt' % (base_path, 'tx/', trial_name)
        rx_path = '%s%s%s/*.p' % (base_path, 'rx/', trial_name)
        tx_files = glob.glob(tx_path)
        rx_files = glob.glob(rx_path)
        tx_dict = self._mk_tx_dict(tx_files)
        rx_dict = self._mk_rx_dict(rx_files)
        print('Rx Dict: ')
        pp.pprint(rx_dict)
        print('Tx Dict: ')
        pp.pprint(tx_dict)
        loss_dict = self._mk_loss_dict(tx_dict, rx_dict)
        return loss_dict

    def calc_flow_rate( self
                      , trial_name
                      , pkt_size
                      , time_frame
                      , trial_len ):
        base_path = self.base_path
        tx_path = '%s%s%s/*.txt' % (base_path, 'tx/', trial_name)
        rx_path = '%s%s%s/*.p' % (base_path, 'rx/', trial_name)
        tx_files = glob.glob(tx_path)
        rx_files = glob.glob(rx_path)
        rx_dict = self._mk_rx_dict(rx_files)
        tx_dict = self._mk_tx_dict(tx_files)
        rx_stats = defaultdict(dict)
        for rx_host, v in rx_dict.items():
            for tx_host, rx_count in v.items():
                rx_stats[tx_host][rx_host] = ((rx_count / float(trial_len)) * pkt_size * 8) / 10**6
       
        return rx_stats



    
