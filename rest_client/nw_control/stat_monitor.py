import requests     as req
import json         as json
import numpy        as np

from collections    import defaultdict

def compute_link_key(source_id, destination_id):
    return tuple(sorted((source_id, destination_id)))

def compute_link_utilization_over_time(link_byte_counts):
    """
    Compute a list of sampled link utilization values based on 
    the byte count samples retrieved from the stat_monitor module.

    link_byte_counts: [byte_count_snapshots]
    byte_count_snapshot: (sourceSwitchId, destinationSwitchId, bytesReceived, bytesSent)

    RETURNS 
        tx_rate_t: (source_id x destination_id) -> link_utilization_in_time_period_t forall. t
    """
    def find_matching_iface_stats(byte_count, source_id, destination_id):
        matching_stats = [d_i for d_i in byte_count
                if d_i["sourceSwitchId"] == source_id and
                d_i["destinationSwitchId"] == destination_id]
        if len(matching_stats) != 1:
            raise ValueError("Unexpected results in find_matching_iface_stats. \
                    Found %d matching iface_stats" % len(matching_stats))
        return matching_stats[0]

    def compute_tx_rate(count_in_bytes):
        return (count_in_bytes * 8) / 10.0 / 2**20

    # pp.pprint(len(link_byte_counts[0])) 
    # First compute the delta between the iface_stats in time_period t_i and the iface_stats
    # in time period t_{i+1}.
    # tx_rate_t: (source_id x destination_id) -> link_utilization_in_time_period_t forall. t
    tx_rate_t = []
    for t_0, t_1 in zip(link_byte_counts, link_byte_counts[1:]):
        byte_count_delta_t = defaultdict(float)
        for iface_stats in t_0:
            source_id = iface_stats["sourceSwitchId"]
            destination_id = iface_stats["destinationSwitchId"]
            t_0_count = iface_stats["bytesSent"] # + iface_stats["bytesReceived"]
            try:
                t_1_stats = find_matching_iface_stats(t_1, source_id, destination_id)
                t_1_count = t_1_stats["bytesSent"] # + t_1_stats["bytesReceived"]
            except ValueError:
                t_1_count = t_0_count

            count_delta = t_1_count - t_0_count
            link_key = compute_link_key(source_id, 
                    destination_id)
            byte_count_delta_t[link_key] += count_delta

        tx_rate_t.append({the_link_key: compute_tx_rate(byte_count_t) 
            for the_link_key, byte_count_t in byte_count_delta_t.items()})
    return tx_rate_t

def compute_mean_link_utilization(link_byte_counts):
    """
    Compute the averge utilization of each link based on the byte count samples
    received from the stat_monitor module.

    RETURNS
        link_util: (source_id x destination_id) -> mean link utilization
    """
    def collect_all_link_keys(link_util_t):
        link_keys = set()
        for t_i in link_util_t:
            for link_key in t_i.keys():
                link_keys.add(link_key)
        return link_keys

    link_util_t = compute_link_utilization_over_time(link_byte_counts)
    link_keys = collect_all_link_keys(link_util_t)
    mean_link_utils = {}
    for link_key in link_keys:

        link_util_over_time = [d_i[link_key] for d_i in link_util_t if link_key in d_i]
        mean_link_util = np.mean(link_util_over_time)
        mean_link_utils[link_key] = mean_link_util

    return mean_link_utils


class OnMonitor:

    def __init__(self, onos_controller_ip, onos_controller_port):
        self._onos_controller_ip        = onos_controller_ip
        self._onos_controller_port      = onos_controller_port
        self._monitor_token             = None
        self._credentials               = ("onos", "rocks")
        self._stop_monitor_response     = None

    def start_monitor(self):
        if self._monitor_token != None:
            raise ValueError("Monitor is already running.")

        on_mon_url = ("http://%s:%d/onos/on-mon/v1/start-monitor" % 
                (self._onos_controller_ip, self._onos_controller_port))
        start_monitor_request = req.post(on_mon_url, auth=self._credentials)
        if start_monitor_request.status_code == 200:
            start_monitor_response = json.loads(start_monitor_request.text)
            self._monitor_token = start_monitor_response["token"]
        else:
            raise ValueError("Failed to start OnMonitor. Status %d, Reason %s." %
                    (start_monitor_request.status_code, start_monitor_request.reason))

    def stop_monitor(self):
        if self._monitor_token == None:
            raise ValueError("Monitor was not running.")

        on_mon_url = ("http://%s:%d/onos/on-mon/v1/stop-monitor?monitor-token=%s" %
                (self._onos_controller_ip, self._onos_controller_port, self._monitor_token))
        stop_monitor_request = req.post(on_mon_url, auth=self._credentials)
        if stop_monitor_request.status_code == 200:
            stop_monitor_response = json.loads(stop_monitor_request.text)
            self._stop_monitor_response = stop_monitor_response
            self._monitor_token = None
        else:
            raise ValueError("Failed to stop OnMonitor. Status %d, Reason %s." % 
                    (stop_monitor_request.status_code, stop_monitor_request.reason))

    def get_monitor_statistics(self):
        if self._stop_monitor_response == None:
            raise ValueError("No results have been collected yet! Did you remember to start/stop the monitor.")
        return [d["netUtilStats"]["utilizationStats"] for d in self._stop_monitor_response]
