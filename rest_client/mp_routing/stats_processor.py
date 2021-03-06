import statistics as stat
from collections import defaultdict
from enum import Enum
import glob as glob
import os.path as os_path
import pickle as pick
import pprint as pp

import matplotlib.pyplot as plt
import numpy as np

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
        print('stats_processor-> _calc_link_util_pps_t: timeframes: ' + str(timeframes))
        link_utils = defaultdict(lambda : defaultdict(list))
        for (sw_dpid, egress_port), count_list in timeframes.items():
            try:
                src_nm, dst_nm = self._get_friendly_link(sw_dpid, egress_port)
            except ValueError:
                continue
            link_utils[src_nm][dst_nm] = count_list
        print('link utils: ' + str(link_utils))
        return link_utils

    def _calc_uplink_port_util_pps( self
                                  , stats_dict
                                  , tranfs_fn = lambda lst : stat.mean(lst)):
        timeframes = self._compute_timeframes(stats_dict)
        link_utils = defaultdict(dict)
        for (sw_dpid, egress_port), count_list in timeframes.items():
            if self._is_host_port(sw_dpid, egress_port):
                sw_name = self._mapper.map_dpid_to_sw(sw_dpid)
                link_utils[sw_name][egress_port] = tranfs_fn(count_list)
        return link_utils

    def _compute_timeframes(self, results_store):
        return { k : list(map(lambda t : t[1] - t[0], zip(v, v[1:]))) for k, v in results_store.items() }

    def _convert_stats(self, stats_dict, conv_fn):
        ret = defaultdict(dict)
        for src_sw, v in stats_dict.items():
            for dst_sw, count in v.items():
                print('count: ' + str(count))
                ret[src_sw][dst_sw] = conv_fn(count)
                print('link util: ' + str(ret[src_sw][dst_sw]))
        return ret

    def _convert_stats_list(self, stats_dict, conv_fn):
        ret = defaultdict(dict)
        for src_sw, v in stats_dict.items():
            for dst_sw, count_list in v.items():
                ret[src_sw][dst_sw] = list(map(conv_fn, count_list))
        print('stats_processor-> _convert_stats_list: ' + str(ret))
        return ret

    def _build_conv_fn(self, pkt_size, time_frame, units=Units.PacketsPerSecond):
        if units == Units.PacketsPerSecond:
            conv_fn = lambda pkts : (pkts / float(time_frame))
        elif units == Units.BitsPerSecond:
            conv_fn = lambda pkts : ((pkts * pkt_size * 8) / float(time_frame))
        elif units == Units.MegaBitsPerSecond:
            print('Correct unit: Mbps')
            conv_fn = lambda pkts : (((pkts * pkt_size * 8) / float(10**6)) / float(time_frame))
        elif units == Units.BytesPerSecond:
            conv_fn = lambda pkts : ((pkts * 1066) / float(time_frame))
        elif units == Units.MegaBytesPerSecond:
            conv_fn = lambda pkts : (((pkts * 1066) / float(10**6)) / float(time_frame))
        return conv_fn

    def _calc_link_util( self
                       , pps_stats
                       , pkt_size
                       , time_frame
                       , units=Units.PacketsPerSecond ):
        conv_fn = self._build_conv_fn(pkt_size, time_frame, units)
        #print('time_frame: ' + str(time_frame))
        #print('conv_fn: ' + str(conv_fn))
        #print('pps_stats: ' + str(pps_stats))
        return self._convert_stats(pps_stats, conv_fn)
    
    def _calc_link_util_list( self
                            , pps_stats
                            , pkt_size
                            , time_frame
                            , units=Units.PacketsPerSecond ):
        conf_fn = self._build_conv_fn(pkt_size, time_frame, units)
        return self._convert_stats_list(pps_stats, conf_fn)

    def calc_link_util( self
                      , stats_dict
                      , pkt_size
                      , time_frame
                      , units=Units.PacketsPerSecond ):
        pps_stats = self._calc_link_util_pps(stats_dict)
        print('pps_stats: ' + str(pps_stats))
        stats = self._calc_link_util(pps_stats, pkt_size, time_frame, units)
        return stats
    
    def calc_link_util_per_t( self
                            , stats_dict
                            , pkt_size
                            , time_frame
                            , units=Units.PacketsPerSecond ):
        pps_stats = self._calc_link_util_pps_t(stats_dict)
        stats = self._calc_link_util_list(pps_stats, pkt_size, time_frame, units)
        return stats

    def calc_ingress_util( self
                         , stats_dict
                         , pkt_size
                         , time_frame
                         , units=Units.PacketsPerSecond ):
        pps_stats = self._calc_uplink_port_util_pps(stats_dict)
        stats = self._calc_link_util(pps_stats, pkt_size, time_frame, units)
        return stats

    def calc_ingress_util_per_t( self
                               , stats_dict
                               , pkt_size
                               , time_frame
                               , units=Units.PacketsPerSecond ):
        pps_stats = self._calc_uplink_port_util_pps(stats_dict, lambda lst : lst)
        stats = self._calc_link_util_list(pps_stats, pkt_size, time_frame, units)
        return stats

    def _get_src_dst_pair(self, file_name):
        base = os_path.basename(file_name)
        toks, _ = os_path.splitext(base)
        toks = toks.split('-')
        src_host, dst_host = int(toks[0].split('_')[1]), int(toks[1])
        return (src_host, dst_host)

    def _mk_tx_dict(self, tx_files):
        tx_dict = defaultdict(lambda : defaultdict(dict))
        for f in tx_files:
            with open(f, 'rb') as fd:
                flow_dict = pick.load(fd)
                for flow_id, flow_info in flow_dict.items():
                    src_host = flow_info['src_host']
                    dst_ip = flow_info['dst_ip']
                    src_port = flow_info['src_port']
                    str = dst_ip.split('.')
                    if str[1] == '0' and str[2] == '168' and str[3] == '192':
                     dst_ip = str[3] + '.' + str[2] + '.' + str[1] + '.' + str[0]
                    dst_hname = self._mapper.reverse_lookup(dst_ip)
                    tok_list = dst_hname.split('.')
                    if tok_list[2] == '168':
                        dst_hname = tok_list[0] + '.of.cpsc.'
                    src_hname = self._mapper.qualify_host_domain(self._mapper.map_sw_to_host(src_host))
                    tx_dict[src_hname][dst_hname][src_port] = flow_info['pkt_count']
                    print('stats_processor-> _mk_tx_dict: tx[src=%s][dst=%s][src_port=%s] = pkt_count:%d'%(src_hname,dst_hname,src_port,flow_info['pkt_count']))
        return tx_dict

    def _mk_rx_dict(self, rx_files):
        rx_dict = defaultdict(lambda : defaultdict(dict))
        for f in rx_files:
            with open(f, 'rb') as fd:
                infos = pick.load(fd)
                for (src_ip, src_port), pkt_count in infos.items():
                    base, _ = os_path.splitext(os_path.basename(f))
                    rx_er = base.split('_')[1]
                    rx_host = self._mapper.qualify_host_domain(self._mapper.map_sw_to_host(rx_er))
                    hostname = self._mapper.reverse_lookup(src_ip)
                    tok_list = hostname.split('.')
                    if tok_list[2] == '168':
                        hostname = tok_list[0] + '.of.cpsc.'
                    rx_dict[rx_host][hostname][src_port] = pkt_count
                    print('stats_processor-> _mk_rx_dict: rx[rx_host=%s][hostname=%s][src_port=%s] = pkt_count:%d'%(rx_host,hostname,src_port,pkt_count))
        return rx_dict
    
    def calc_pkt_loss(self, tx_pkts, rx_pkts):
        pkt_loss = (tx_pkts - rx_pkts) / float(tx_pkts)
        return pkt_loss
    
    def _mk_loss_dict(self, tx_dict, rx_dict):
        loss_dict = defaultdict(lambda : defaultdict(dict))
        for src_host, vs in tx_dict.items():
            for dst_host, flows in vs.items():
                for src_port, tx_pkts in flows.items():
                    try:
                        rx_pkts = rx_dict[dst_host][src_host][src_port]
                    except KeyError:
                        print('ERROR: RxDict lookup failed. ignoring flow %s -> %s' %
                            (src_host, dst_host))
                        continue
                    loss_dict[src_host][dst_host][src_port] = self.calc_pkt_loss(tx_pkts, rx_pkts)
        return loss_dict
    
    def calc_loss_rates(self, trial_name):
        """
        This method makes some irritating assumptions about file paths
        to the pkl and txt files containing the packet drop rate
        statistics
        """
        base_path = self.base_path
        tx_path = '%s%s%s/*.p' % (base_path, 'tx/', trial_name)
        rx_path = '%s%s%s/*.p' % (base_path, 'rx/', trial_name)
        print('tx_path: ' + str(tx_path))
        print('rx_path: ' + str(rx_path))
        tx_files = glob.glob(tx_path)
        rx_files = glob.glob(rx_path)
        tx_dict = self._mk_tx_dict(tx_files)
        rx_dict = self._mk_rx_dict(rx_files)
        print('tx_dict: ' + str(tx_dict))
        print('rx_dict: ' + str(rx_dict))
        loss_dict = self._mk_loss_dict(tx_dict, rx_dict)
        
        return loss_dict

    def calc_flow_rate( self
                      , trial_name
                      , pkt_size
                      , time_frame
                      , trial_len ):
        base_path = self.base_path
        tx_path = '%s%s%s/*.p' % (base_path, 'tx/', trial_name)
        rx_path = '%s%s%s/*.p' % (base_path, 'rx/', trial_name)
        tx_files = glob.glob(tx_path)
        rx_files = glob.glob(rx_path)
        rx_dict = self._mk_rx_dict(rx_files)
        tx_dict = self._mk_tx_dict(tx_files)
        rx_stats = defaultdict(lambda : defaultdict(dict))
        for rx_host, v in rx_dict.items():
            for tx_host, flows in v.items():
                for src_port, rx_count in flows.items():
                    rx_stats[tx_host][rx_host][src_port] = ((rx_count / float(trial_len)) * pkt_size * 8) / 10**6

        return rx_stats

class Grapher:

    def __init__(self):
        pass

    def graph_timeframes( self
                        , axes
                        , stats_list
                        , names = ['timeframe']
                        , show_plot = False 
                        , positions = [1] ):
        network_util = stats_list
        plt.boxplot(network_util, labels=names)
        plt.ylabel('Link Utilization (Mbps)')
    
    def graph_util_over_time( self
                            , stats_list
                            , name = 'util_per_t'
                            , show_plot = False ):
        for src_sw, v in stats_list.items():
            for dst_sw, count_list in v.items():
                plt.plot(count_list)
        plt.title(name)
        plt.xlabel('Time')
        plt.ylabel('Link Utilization (Mbps)')
        if show_plot:
            plt.show()
        plt.savefig('./%s.png' % name)
        plt.cla()

    def graph_loss_cdf( self
                      , axes
                      , stats_list
                      , name ):
        pp.pprint(stats_list)
        loss_list = [ ll for d in stats_list.values() for d1 in d.values() for ll in d1.values() ]
        print(loss_list)
        sum_val = sum(loss_list)
        normalized = []
        for loss_rate in loss_list:
            normalized.append(0 if sum_val == 0 else loss_rate / sum_val)
        CDF = np.cumsum(sorted(normalized))
        plt.title('Loss CDF')
        plt.ylabel('P{x < X}')
        plt.xlabel('Loss Rate')
        axes.plot(sorted(loss_list), CDF, label=name)

