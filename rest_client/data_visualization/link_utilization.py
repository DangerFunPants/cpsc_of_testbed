
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json 
import pprint                       as pp
import pathlib                      as path
import pygraphviz                   as pgv

import nw_control.topo_mapper       as topo_mapper
import nw_control.util              as util
import data_visualization.params    as cfg
import port_mirroring.params        as pm_cfg
import port_mirroring.util          as pm_util

from collections        import defaultdict
from statistics         import mean

def save_figure(figure_name, **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    plt.savefig(str(p), **kwargs)

def read_json_response_from_file(file_path):
    with file_path.open("r") as fd:
        text = fd.read()

    root_response_json = json.loads(text)
    actual_response_json = root_response_json
    return actual_response_json

def compute_initial_byte_counts(byte_counts_per_time_period):
    return byte_counts_per_time_period[0]

def subtract_counts(count_a, count_b):
    diff = defaultdict(dict)
    for s, t in count_a.items():
        for d, b in t.items():
            try:
                diff[s][d] = b - count_b[s][d]
            except KeyError:
                print("Key error")
                continue
    return diff

def compute_utilization_from_byte_counts(byte_count, link_capacity):
    return {s: {d: b / link_capacity for d, b in t.items()} for s, t in byte_count.items()}

def generate_network_util_data_over_time(util_results):
    byte_counts_per_time_period = []
    for link_util_dict in util_results:
        # Each results_list represents a snapshot of the network at a point in time.
        results_list = link_util_dict["netUtilStats"]["utilizationStats"]
        # Each results_set represents a particular link in the network at a given time.
        byte_counts = defaultdict(dict)
        for results_set in results_list:
            # Arbitrarily use the source counts, collect them first
            source_switch = results_set["sourceSwitchId"]
            destination_switch = results_set["destinationSwitchId"]
            byte_counts[source_switch][destination_switch] = results_set["bytesSent"] + results_set["bytesReceived"]
        byte_counts_per_time_period.append(byte_counts)
    
    util_in_time_period = []
    initial_byte_counts = compute_initial_byte_counts(byte_counts_per_time_period)
    for last_count, current_count in zip(byte_counts_per_time_period, byte_counts_per_time_period[1:]):
        differential_count = subtract_counts(current_count, last_count)
        link_utilization_snapshot = compute_utilization_from_byte_counts(differential_count, 10)
        util_in_time_period.append(link_utilization_snapshot)

    pp.pprint(util_in_time_period)
    return util_in_time_period

def graph_link_utilization(link_utilization_data):
    link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
    print("link_ids", len(link_ids))
    mean_utils  = []
    labels      = []
    collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
    id_to_dpid = topo_mapper.get_and_validate_onos_topo(pm_cfg.target_topo_path)
    dpid_to_id = {v: k for k, v in id_to_dpid.items()}
    for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
        link_utils_over_time = []
        for time_idx, net_snapshot in enumerate(link_utilization_data):
            try:
                link_utils_over_time.append(net_snapshot[s][d])
            except KeyError:
                print("net_snapshot at time %d did not contain link %s -> %s" % (time_idx, s, d))

        mean_utils.append(util.bytes_per_second_to_mbps(mean(link_utils_over_time)))
        labels.append(dpid_to_id[s])

    ind = np.arange(1, 12)
    width = 0.35
    fig, ax = plt.subplots()

    ys = [mu for mu, l in sorted(zip(mean_utils, labels), key=lambda t: t[1])]
    xs = labels 
    ax.set_xticks(ind+(width/2))
    ax.set_xticklabels(range(1, 12))
    ax.bar(ind-(width/2), ys, width, label="measured", color="skyblue", hatch=".")

    flows           = pm_util.parse_flows_from_file(pm_cfg.flow_file_path)
    solutions       = pm_util.parse_solutions_from_file(pm_cfg.solution_file_path)
    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        print("mirror_id: %d" % mirroring_switch_for_flow)
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    ys = []
    xs = []
    for switch_id in range(1, 12):
        aggregate_rate = mirroring_utils[switch_id]
        xs.append(switch_id)
        ys.append(aggregate_rate * 100)
    
    ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", label="allocated") 
    plt.legend(loc="best")
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Node ID")
    plt.ylabel("Mean Mirroring Port Throughput ($\\frac{Mb}{s}$)")
    save_figure("link-util.pdf")
    plt.clf()

def main():
    mirroring_ports = topo_mapper.get_switch_mirroring_ports()
    pp.pprint(mirroring_ports)
    util_results = read_json_response_from_file(path.Path("./utilization-results.txt"))
    results_over_time = generate_network_util_data_over_time(util_results)
    graph_link_utilization(results_over_time)

