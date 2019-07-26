
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

from collections                    import defaultdict
from statistics                     import mean
from port_mirroring.trial_provider  import FlowDefinition, SolutionDefinition

LEGEND_HEIGHT = 1.125

def save_figure(figure_name, **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    plt.savefig(str(p), **kwargs)
    plt.clf()

def read_json_response_from_file(file_path):
    text = file_path.read_text()
    return read_json_response(text)

def read_json_response(text):
    root_response_json = json.loads(text)
    return root_response_json 

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

def compute_network_util_over_time(util_results):
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

    return util_in_time_period

def compute_most_used_mirroring_port(flows, solutions):
    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    return max(mirroring_utils.items(), key=lambda t: t[1])[0]

def compute_theoretical_util(flows, solutions):
    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    return max(mirroring_utils.items(), key=lambda t: t[1])[1] 

def read_results(results_repository, provider_name, trial_name):
    schema_variables = { "provider-name"        : provider_name
                       , "trial-name"           : trial_name    
                       }
    files = [ "utilization-results.txt"
            , "topo"
            , "flows"
            , "switches"
            , "solutions"
            ]
    results = results_repository.read_trial_results(schema_variables, files)
    topo = results["topo"]
    topo                = results["topo"]
    flows               = FlowDefinition.deserialize(results["flows"])
    solutions           = SolutionDefinition.deserialize(results["solutions"])
    utilization_json    = read_json_response(results["utilization-results.txt"])
    net_utilization     = compute_network_util_over_time(utilization_json)
    return topo, flows, solutions, net_utilization

def generate_max_mirror_port_utilization_bar_plot(results_repository):
    utilization_data, _     = compute_theoretical_and_actual_mean_utilization(results_repository)
    actual_error            = compute_theoretical_and_actual_error(results_repository)

    std_deviations = defaultdict(list)
    for provider_name, data_list in actual_error.items():
        for flow_count, data in data_list:
            std_deviations[provider_name].append(np.std(
                [util.bytes_per_second_to_mbps(d_i) for d_i in data]))

    width = 0.35
    ind = np.arange(1, 6) 
    fig, ax = plt.subplots()
    xs = [t[0] for t in utilization_data["approx"]]
    ys = [util.bytes_per_second_to_mbps(t[1]) for t in utilization_data["approx"]]
    ax.bar(ind-(width/2), ys, width, color="skyblue", hatch=".", tick_label=xs, label="BiSec",
            yerr=std_deviations["approx"], ecolor="black")

    xs = [t[0] for t in utilization_data["optimal"]]
    ys = [util.bytes_per_second_to_mbps(t[1]) for t in utilization_data["optimal"]]
    ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", tick_label=xs, label="Optimal",
            yerr=std_deviations["optimal"], ecolor="black")

    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, LEGEND_HEIGHT), shadow=True, ncol=2)

    save_figure("plot-one.pdf")

def compute_theoretical_and_actual_error(results_repository):
    utilization_data = defaultdict(list)

    for provider_name in ["optimal", "approx"]:
        for trial_idx in range(5):
            trial_name = "sub-trial-%d" % trial_idx
            topo, flows, solutions, net_utilization = read_results(results_repository,
                    provider_name, trial_name)

            most_used_mirroring_port = compute_most_used_mirroring_port(flows, solutions)
            id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
            mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
            collector_switch_dpid = topo_mapper.get_collector_switch_dpid()

            utilization = [util_at_time_t[mirror_port_dpid][collector_switch_dpid]
                    for util_at_time_t in net_utilization]
            utilization_data[provider_name].append((len(flows), utilization))

    return utilization_data

def compute_theoretical_and_actual_mean_utilization(results_repository):
    utilization_data = defaultdict(list)
    theoretical_data = defaultdict(list)

    for provider_name in ["optimal", "approx"]:
        for trial_idx in range(5):
            trial_name = "sub-trial-%d" % trial_idx
            topo, flows, solutions, net_utilization = read_results(results_repository, 
                    provider_name, trial_name)

            most_used_mirroring_port = compute_most_used_mirroring_port(flows, solutions)
            id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
            mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
            collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
            
            utilization = mean([util_at_time_t[mirror_port_dpid][collector_switch_dpid]
                for util_at_time_t in net_utilization])
            theoretical_utilization = compute_theoretical_util(flows, solutions)
            utilization_data[provider_name].append((len(flows), utilization))
            theoretical_data[provider_name].append((len(flows), theoretical_utilization))

    return utilization_data, theoretical_data

def generate_mirroring_port_utilization_bar_plot(results_repository):
    topo, flows, solutions, link_utilization_data = read_results(results_repository, "approx", "sub-trial-4")
    link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
    mean_utils  = []
    labels      = []
    errors      = []
    collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
    id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
    dpid_to_id = {v: k for k, v in id_to_dpid.items()}
    for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
        link_utils_over_time = []
        for time_idx, net_snapshot in enumerate(link_utilization_data):
            try:
                link_utils_over_time.append(net_snapshot[s][d])
            except KeyError:
                print("net_snapshot at time %d did not contain link %s -> %s" % (time_idx, s, d))
        mean_utils.append(util.bytes_per_second_to_mbps(mean(link_utils_over_time)))
        errors.append(util.bytes_per_second_to_mbps(np.std(link_utils_over_time)))
        labels.append(dpid_to_id[s])

    ind = np.arange(1, 12)
    width = 0.35
    fig, ax = plt.subplots()

    ys = [mu for mu, l in sorted(zip(mean_utils, labels), key=lambda t: t[1])]
    xs = labels
    errors = [e for e, l in sorted(zip(errors, labels), key=lambda t: t[1])]
    ax.set_xticks(ind+(width/2))
    ax.set_xticklabels(range(1, 12))
    ax.bar(ind-(width/2), ys, width, label="Measured", color="skyblue", hatch=".",
            yerr=errors, ecolor="black")

    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    ys = []
    xs = []
    for switch_id in range(1, 12):
        aggregate_rate = mirroring_utils[switch_id]
        xs.append(switch_id)
        ys.append(aggregate_rate * 100)
    
    ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", label="Expected") 
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, LEGEND_HEIGHT), shadow=True, ncol=2)
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Switch ID")
    plt.ylabel("Mean Mirroring Port Rate ($\\frac{Mb}{s}$)")
    save_figure("plot-three.pdf")
    plt.clf()


def generate_theoretical_vs_actual_utilization_bar_plot(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(results_repository)
    actual_error = compute_theoretical_and_actual_error(results_repository)
    std_deviations = defaultdict(list)
    for provider_name, data_list in actual_error.items():
        for flow_count, data in data_list:
            std_deviations[provider_name].append(np.std(
                [util.bytes_per_second_to_mbps(d_i) for d_i in data]))

    width = 0.35
    ind = np.arange(1, 6) 
    fig, ax = plt.subplots()

    xs = [t[0] for t in utilization_data["approx"]]
    ys = [util.bytes_per_second_to_mbps(t[1]) for t in utilization_data["approx"]]
    ax.bar(ind-(width/2), ys, width, color="skyblue", hatch=".", tick_label=xs, label="Measured",
            yerr=std_deviations["approx"], ecolor="black")
    
    xs = [t[0] for t in theoretical_data["approx"]]
    ys = [t[1] * 100 for t in theoretical_data["approx"]]
    ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", tick_label=xs, label="Expected")

    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, LEGEND_HEIGHT), shadow=True, ncol=2)

    save_figure("plot-two.pdf")

def generate_approx_vs_optimal_theoretical_utilization_bar_plot(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(results_repository)

    width = 0.35
    ind = np.arange(1, 6) 
    fig, ax = plt.subplots()

    xs = [t[0] for t in theoretical_data["approx"]]
    ys = [t[1] * 100 for t in theoretical_data["approx"]]
    ax.bar(ind-(width/2), ys, width, color="skyblue", hatch=".", tick_label=xs, label="approx")

    xs = [t[0] for t in theoretical_data["optimal"]]
    ys = [t[1] * 100 for t in theoretical_data["optimal"]]
    ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", tick_label=xs, label="optimal")

    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring rate ($\\frac{Mb}{s}$)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, LEGEND_HEIGHT), shadow=True, ncol=2)

    save_figure("approx-vs-optimal-theoretical.pdf")
    
