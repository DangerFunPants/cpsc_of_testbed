import statistics as stat
from collections import defaultdict
from enum import Enum

class Units(Enum):
    PacketsPerSecond = 0
    MegaBitsPerSecond = 1
    BitsPerSecond = 2
    BytesPerSecond = 3
    MegaBytesPerSecond = 4

class StatsProcessor:
    def __init__(self, mapper, of_proc):
        self._mapper = mapper
        self._of_proc = of_proc

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

    def _calc_link_util_pps(self, stats_dict, pkt_size, time_frame):
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

    def _compute_timeframes(self, results_store):
        return { k : list(map(lambda t : t[1] - t[0], zip(v, v[1:]))) for k, v in results_store.items() }

    def _convert_stats(self, stats_dict, conv_fn):
        ret = defaultdict(dict)
        for src_sw, v in stats_dict.items():
            for dst_sw, count in v.items():
                ret[src_sw][dst_sw] = conv_fn(count)
        return ret
    
    def calc_link_util(self, stats_dict, pkt_size, time_frame, units=Units.PacketsPerSecond):
        pps_stats = self._calc_link_util_pps(stats_dict, pkt_size, time_frame)
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
        return self._convert_stats(pps_stats, conv_fn)




    
