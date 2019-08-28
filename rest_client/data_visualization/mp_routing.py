
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json
import pprint                       as pp
import pathlib                      as path
import itertools                    as itertools
import random                       as rand

import mp_routing.vle_trial                     as vle_trial
import data_visualization.params                as cfg
import data_visualization.helpers               as helpers
import traffic_analysis.core_taps               as core_taps
import traffic_analysis.heterogeneous_links     as heterogeneous_links

from collections                    import defaultdict
from statistics                     import mean

from data_visualization.helpers     import marker_style, line_style, line_color

FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

plt.rc("text", usetex=True)
plt.rc("font", **cfg.FONT)
matplotlib.rcParams['text.latex.preamble']  = [ r"\usepackage{amsmath}"
                                              , r"\usepackage{amssymb}"
                                              , r"\usepackage{amsfonts}"
                                              , r"\usepackage{amsthm}"
                                              , r"\usepackage{graphics}"
                                              ]
matplotlib.rcParams["xtick.direction"]      = "in"
matplotlib.rcParams["ytick.direction"]      = "in"

# TRIAL_TYPES     = ["link-embedding", "average", "percentile"]
TRIAL_TYPES     = ["average", "percentile", "link-embedding"]
LABELS          = ["Average", "$95$-Percentile", "epVLE"]
# LABELS          = ["epVLE", "Average", "$95$-Percentile"]
LABEL_NAMES     = [helpers.trial_name_font(l_i) for l_i in LABELS]
SEED_NUMBERS    = [830656277, 3654904804, 1736873850]

def save_figure(figure_name, **kwargs):
    p = FIGURE_OUTPUT_PATH.joinpath(figure_name)
    # plt.show()
    plt.savefig(str(p), **kwargs)

def read_utilization_results_from_file(utilization_results_file):
    json_text = utilization_results_file.read_text()
    # root_object :: time_idx -> utilization_description
    # count_description :: { destinationSwitchId
    #                      , sourceSwitchId
    #                      , bytesReceived
    #                      , bytesSent
    #                      , packetsReceived
    #                      , packetsSent
    #                      }

    root_object = [net_snapshot["netUtilStats"]["utilizationStats"] 
            for net_snapshot in json.loads(json_text)]
    return root_object

def compute_link_utilization(byte_count_in_time_period, time_period):
    return ((byte_count_in_time_period / time_period) * 8) / 10**6

# [count_description] -> [utilization_description]
# utilization_description :: { sourceSwitchId
#                            , destinationSwitchId
#                            , linkUtilization
#                            }
def compute_link_utilization_over_time(utilization_results):
    zipped_descriptions = zip(utilization_results, utilization_results[1:])
    utilization_descriptions = []
    for previous_count_descriptions, current_count_descriptions in zipped_descriptions:
        byte_count_diff = (current_count_descriptions["bytesSent"] -
                previous_count_descriptions["bytesSent"])
        packet_count_diff = (current_count_descriptions["packetsSent"] -
                previous_count_descriptions["bytesSent"])
        link_utilization = compute_link_utilization(byte_count_diff, 10)
        utilization_description = { "sourceSwitchId"        : source_dpid
                                  , "destinationSwitchId"   : destination_dpid
                                  , "linkUtilization"       : link_utilization
                                  }
        utilization_descriptions.append(utilization_description)
    return utilization_descriptions

def generate_average_link_utilization_plot(utilization_results):
    link_utilization_over_time = compute_link_utilization_over_time(utilization_results)
    average_link_utilizations = {}
    for utilization_description in link_utilization_over_time:
        source_dpid = utilization_description["sourceSwitchId"]
        destination_dpid = utilization_description["destinationSwitchId"]
        link_utilization

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

    # return {s: {d: b - count_b[s][d] for d, b in t.items()} for s, t in count_a.items()}
    return diff

def compute_utilization_from_byte_counts(byte_count, link_capacity):
    return {s: {d: b / link_capacity for d, b in t.items()} for s, t in byte_count.items()}

# return {source_id: destination_id: utilization} forall source_id, destination_id
def compute_network_util_over_time(util_results):
    byte_counts_per_time_period = []
    for link_util_dict in util_results:
        # Each results_list represents a snapshot of the network at a point in time.
        results_list = link_util_dict
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
    # mean_utils = [mean([net_snapshot[s][d] for net_snapshot in link_utilization_data]) for s, d in link_ids]
    mean_utils = []
    for s, d in link_ids:
        link_utils_over_time = []
        for time_idx, net_snapshot in enumerate(link_utilization_data):
            try:
                link_utils_over_time.append(net_snapshot[s][d])
            except KeyError:
                print("net_snapshot at time %d did not contain link %s -> %s" % (time_idx, s, d))

        mean_utils.append((mean(link_utils_over_time) * 8) / 10**6)

    # ys = [b for s, t in d.items() for d, b in t.items()]
    ys = mean_utils
    pp.pprint(ys)
    print(mean(ys))
    xs = np.arange(len(ys))
    plt.bar(xs, ys)
    save_figure("link-util.pdf")
    plt.clf()

def read_results(results_repository, trial_type, seed_number):
    schema_variables = { "trial-name"   : seed_number
                       , "trial-type"   : trial_type
                       , "seed-number"  : str(seed_number)
                       }
    # schema_variables = { "trial-type"   : trial_type
    #                    , "seed-number"  : str(seed_number)
    #                    }

    files = [ "utilization-results.txt"
            , "vle-trial.json"
            , "end-host-results.json"
            ]


    results = results_repository.read_trial_results(schema_variables, files)

    utilization_results     = json.loads(results["utilization-results.txt"])
    utilization_results     = [net_snapshot["netUtilStats"]["utilizationStats"]
            for net_snapshot in json.loads(results["utilization-results.txt"])]
    the_vle_trial           = vle_trial.VleTrial.from_json(results["vle-trial.json"])
    end_host_results        = json.loads(results["end-host-results.json"])
    return utilization_results, the_vle_trial, end_host_results

def generate_link_utilization_bar_plot(results_repository, trial_type, trial_name):
    utilization_results, the_vle_trial, end_host_results = read_results(results_repository, 
            trial_type, trial_name)
    link_utilization_data = compute_network_util_over_time(utilization_results)
    graph_link_utilization(link_utilization_data)

def generate_loss_rates(results_repository, trial_type, seed_number):
    utilization_results, the_vle_trial, end_host_results = read_results(results_repository, 
            trial_type, seed_number)
    pp.pprint(end_host_results)
    packet_loss_rates = defaultdict(list)
    for source_host, destination_host_to_packet_counts in end_host_results.items():
        for destination_host, packet_counts_list in destination_host_to_packet_counts.items():
            for packet_counts in packet_counts_list:
                receiver_count  = packet_counts["receiver-count"]
                sender_count    = packet_counts["sender-count"]
                source_id = int(source_host)
                destination_id = int(destination_host)
                packet_loss_rates[source_id, destination_id].append(abs(sender_count - receiver_count) / sender_count)

    pp.pprint(packet_loss_rates)
    all_loss_rates = []
    for loss_rate_list in packet_loss_rates.values():
        all_loss_rates.extend(loss_rate_list)

    return all_loss_rates

def generate_loss_rate_cdf(results_repository):
    trial_name = "test-trial-830656277" 
    seed_numbers = [trial_name]
    for idx, trial_type in enumerate(TRIAL_TYPES):
        loss_rates_for_seed_number = []
        for seed_number in seed_numbers:
            loss_rate_per_flow = generate_loss_rates(results_repository, 
                    trial_type, seed_number)
            xs = [0.0]
            ys = [0.0]
            for ctr, loss_rate in enumerate(sorted(loss_rate_per_flow)):
                xs.append(loss_rate)
                ys.append((ctr + 1) / len(loss_rate_per_flow))
            plt.plot(xs, ys, linestyle="-",
                    marker=helpers.marker_style(idx),
                    label=LABEL_NAMES[idx], 
                    color=helpers.line_color(idx))
    plt.rc("font", **cfg.FONT)
    plt.rc("legend", edgecolor="black")
    # xtick_locations = [200, 400, 600, 800, 1000]
    plt.xlim(0.0)
    plt.ylim(0.0, 1.0)
    xtick_locations, xtick_labels = plt.xticks()
    ytick_locations, ytick_labels = plt.yticks()
    plt.xticks(xtick_locations[1:], [helpers.tick_font(x_i, "%.2f") for x_i in xtick_locations][1:])
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i, "%.1f") for y_i in ytick_locations][1:])
    plt.ylabel("CDF", **cfg.AXIS_LABELS)
    helpers.save_figure("loss-rate-cdf.pdf", 1)

def generate_flow_rate_plot(results_repository):
    trial_name = "test-trial-830656277" 
    utiliztation_results, the_vle_trial, end_host_results = read_results(results_repository,
            "link-embedding", trial_name)
    pp.pprint(the_vle_trial.actual_flow_tx_rates) 
    for flow_rates in the_vle_trial.actual_flow_tx_rates[:5]:
        plt.plot(np.arange(len(flow_rates)), flow_rates)

    # plt.rc('text', usetex=True)
    plt.xlim(0, 59)
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Time", **cfg.AXIS_LABELS)
    plt.ylabel("Transmission Rate (Mbps)", **cfg.AXIS_LABELS)
    xtick_locations, xtick_labels = plt.xticks()
    ytick_locations, ytick_lables = plt.yticks()
    plt.xticks(xtick_locations[1:], ["" for x_i in xtick_locations])
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i, "%.0f") for y_i in ytick_locations][1:])

    # plt.legend(ncol=2, **cfg.LEGEND)
    helpers.save_figure("actual-trace-tx-rates.pdf", 2, no_legend=True)

def generate_flow_means_plot():
    tx_rate_list, mean_flow_tx_rates, std_dev_flow_tx_rates = core_taps.get_rates_for_flows()

    number_of_flows_to_plot = 40
    plt.errorbar([idx+1 for idx in range(number_of_flows_to_plot)], 
            mean_flow_tx_rates[:number_of_flows_to_plot], color="red", marker="D",
            yerr=std_dev_flow_tx_rates[:number_of_flows_to_plot], linestyle="",
            capsize=2)

    plt.rc('font', **cfg.FONT)
    plt.xlim(0, number_of_flows_to_plot)
    plt.ylabel("Mean Transmission Rate (Mbps)", **cfg.AXIS_LABELS)
    plt.xlabel("Virtual Links", **cfg.AXIS_LABELS)
    xtick_locations, xtick_labels = plt.xticks()
    ytick_locations, ytick_lables = plt.yticks()
    plt.xticks(xtick_locations[1:], ["" for x_i in xtick_locations][1:])
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i, "%.0f") for y_i in ytick_locations][1:])

    helpers.save_figure("mean-trace-tx-rates.pdf", 2, no_legend=True)

def expected_link_utilization(results_repository, trial_type, trial_name):
    utilization_results, the_vle_trial, end_host_results = read_results(results_repository,
            trial_type, trial_name)
    link_utilization = defaultdict(float)
    for flow in the_vle_trial.solver_results.flows:
        flow_rate = flow.rate
        for path in flow.paths:
            for u, v in zip(path.nodes, path.nodes[1:]):
                fraction = path.fraction
                # link_utilization[u, v] += flow_rate * fraction
                [u, v] = sorted([u, v])
                link_utilization[u, v] += flow_rate * fraction

    pp.pprint(link_utilization)
    print(mean(link_utilization.values()))

def generate_link_utilization_box_plot(results_repository):
    list_of_mean_utils = []
    for trial_type in TRIAL_TYPES:
        mean_link_utils_per_seed_number = []
        for idx, seed_number in enumerate(["test-trial-830656277"]):
            utilization_results, the_vle_trial, end_host_results = read_results(results_repository, 
                    trial_type, seed_number)
            link_utilization_data = compute_network_util_over_time(utilization_results)
            
            link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
            mean_utils = {}
            for s, d in link_ids:
                link_utils_over_time = []
                for time_idx, net_snapshot in enumerate(link_utilization_data):
                    try:
                        link_utils_over_time.append(net_snapshot[s][d])
                    except KeyError:
                        print("net_snapshot at time %d did not contain link %s -> %s" % 
                                (time_idx, s, d))

                mean_utils[s, d] = ((mean(link_utils_over_time) * 8) / 10**6 / 1000)

            list_of_mean_utils.append(mean_utils)
    pp.pprint([list(v.values()) for v in list_of_mean_utils])
    bp = plt.boxplot([list(v.values()) for v in list_of_mean_utils], labels=LABEL_NAMES,
            whiskerprops={"linestyle":"--"},
            flierprops={"marker": "x", "markerfacecolor": "red", "markeredgecolor": "red"})
    
    for element in ["boxes"]:
        plt.setp(bp[element], color="blue")

    plt.setp(bp["medians"], color="red")

    plt.rc("font", **cfg.FONT)
    plt.rc("legend", edgecolor="black")
    # xtick_locations = [200, 400, 600, 800, 1000]
    # ytick_locations = [2, 4, 6, 8, 10, 12, 14]
    ytick_locations, _ = plt.yticks()
    plt.yticks(ytick_locations, [helpers.tick_font(y_i, "%.1f") for y_i in ytick_locations])
    plt.ylabel("Link Utilization", **cfg.AXIS_LABELS)
    helpers.save_figure("link-utilization-box-plot.pdf", 3, no_legend=True)

def generate_topo_utilization_graph(results_repository, trial_type, trial_name):
    def get_node_set(util_results):
        node_set = set()
        for results_list in util_results:
            for results_set in results_list:
                node_set.add(results_set["sourceSwitchId"])
                node_set.add(results_set["destinationSwitchId"])
        return node_set

    def get_link_set(util_results):
        link_set = set()
        for results_list in util_results:
            for results_set in results_list:
                link_set.add((results_set["sourceSwitchId"], results_set["destinationSwitchId"]))
                link_set.add((results_set["destinationSwitchId"], results_set["sourceSwitchId"]))
        return link_set

    def generate_graph_from_utilization_results(util_results):
        net_topo = nx.Graph()
        for node_id in get_node_set(util_results):
            net_topo.add_node(node_id)

        for u, v in get_link_set(util_results):
            net_topo.add_edge(u, v)

        return net_topo

    def sub_vectors(v1, v2):
        return tuple([v1_i - v2_i for v1_i, v2_i in zip(v1, v2)])

    def scale(v, u):
        return tuple([v_i*u for v_i in v])

    def add_vectors(v1, v2):
        return tuple([v1_i + v2_i for v1_i, v2_i in zip(v1, v2)])
            
    def interp_for_gradient(init_pos, final_pos, u):
        v_hat = sub_vectors(final_pos, init_pos) 
        scaled = scale(v_hat, u)
        c = add_vectors(init_pos, scaled)
        return c

    utilization_results, _, _ = read_results(results_repository, trial_type, trial_name)
    net_topo = generate_graph_from_utilization_results(utilization_results)
    # seed_number = rand.randint(0, 2**32)
    seed_number = 1107035453
    layout = lambda g: nx.spring_layout(g, seed=seed_number)
    link_utilization_data = compute_network_util_over_time(utilization_results)
    link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
    mean_utils = {}
    for s, d in link_ids:
        link_utils_over_time = []
        for time_idx, net_snapshot in enumerate(link_utilization_data):
            try:
                link_utils_over_time.append(net_snapshot[s][d])
            except KeyError as ex:
                print("net_snapshot at time %d did not contain link %s -> %s" % (time_idx, s, d))
        mean_utils[(s, d)] = (mean(link_utils_over_time) * 8) / (10**6 * 1000)

    cs = []
    max_utilization_value = 1000 # max(mean_utils.values())
    color_map_name = "coolwarm"
    cm = plt.get_cmap(color_map_name)
    plt.set_cmap(color_map_name)
    for (u, v) in net_topo.edges():
        u_val = mean_utils[u, v]
        # color_tuple = ((u_val / max_utilization_value), 0, 0)
        # cs.append(color_tuple)
        cs.append(cm(u_val))

    node_colors = []
    host_set = set()
    for node_id in net_topo.nodes():
        if node_id in host_set:
            node_colors.append("r")
        else:
            node_colors.append("skyblue")

    
    pp.pprint(cs)
    graph_pos = layout(net_topo)
    nx.draw_networkx_edges(net_topo, pos=graph_pos, edge_color=cs, edge_cmap=cm)
    nx.draw_networkx_nodes(net_topo, pos=graph_pos, node_color=node_colors, node_size=100)
    plt.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(vmin=0, vmax=1))
    sm._A = []
    plt.colorbar(sm)
    helpers.save_figure("net-topo-link-util.pdf")
    plt.clf()
    pp.pprint(min(mean_utils.values()))
    print(seed_number)

def generate_throughput_over_time_plot(data_file):
    def read_literal_from_file(data_file):
        with data_file.open("r") as fd:
            python_literal = eval(fd.read())
        return python_literal

    path_id_to_ratio_map = { 4  : 0.5
                           , 8  : 0.3
                           , 12 : 0.2
                           }
    path_to_tputs = read_literal_from_file(data_file)
    for plot_idx, (path_id, tputs) in enumerate(sorted(path_to_tputs.items(), key=lambda t: t[0])):
        tputs = tputs[1:11]
        xs = np.arange(len(tputs))
        plt.plot(xs, tputs, linestyle="-.", marker=marker_style(plot_idx),
                color=line_color(plot_idx))
        plt.plot(np.arange(len(tputs)), 
                [path_id_to_ratio_map[path_id] for _ in range(len(tputs))],
                color=line_color(plot_idx), linestyle="-", linewidth=0.75)
    

    lines = [matplotlib.lines.Line2D([0], [0], c="black", linestyle=s_i, linewidth=width)
            for s_i, width in [("-", 0.75), ("-.", 1.0)]]
    legend_labels = ["\\Large{expected throughput}", "\\Large{actual throughput}"]
    plt.legend(lines, legend_labels, ncol=1, **cfg.LEGEND)

    plt.ylim(0.0, 0.6)
    xtick_locations, xtick_labels = plt.xticks()
    plt.xticks(xtick_locations[1:-1], ["" for _ in xtick_locations][1:-1])
    ytick_locations, ytick_labels = plt.yticks()
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i) for y_i in ytick_locations][1:])

    plt.xlabel("Time", **cfg.AXIS_LABELS)
    plt.ylabel("Normalized Throughput", **cfg.AXIS_LABELS)

    helpers.save_figure("per-path-throughput.pdf", no_legend=True)

def generate_traffic_on_path_bar_plot(data_file):
    def read_literal_from_file(data_file):
        with data_file.open("r") as fd:
            python_literal = eval(fd.read())
        return python_literal
    path_data = read_literal_from_file(data_file)
    xs = []
    ys = []
    target_path_ratios = [0.5, 0.3, 0.2]
    cs = []
    
    bar_width = 0.2
    pos = 0.1
    for path_idx, (k, v) in enumerate(sorted(path_data.items(), key=lambda t: t[1], reverse=True)):
        y_val = v / sum(path_data.values())
        cs.append("blue")
        cs.append("green")
        plt.bar(pos-0.01, y_val, bar_width, color="gray", edgecolor="black")
        pos += bar_width
        plt.bar(pos+0.01, target_path_ratios[path_idx], bar_width, color="blue",
                edgecolor="black")
        pos += bar_width

        pos += 0.1
        print("VALUE: %f" % (abs(y_val - target_path_ratios[path_idx]) / target_path_ratios[path_idx]))


    # labels=["Path %d" % path_idx for path_idx in range(1, 4)]
    # plt.bar(xs, ys, edgecolor="black", color=cs)
    legend_labels = ["\\Large{expected data volume}", "\\Large{actual data volume}"]
    legend_colors = ["blue", "gray"]
    patches = [matplotlib.patches.Patch(color=c, label=l, edgecolor="black") 
            for c, l in zip(legend_colors, legend_labels)]
    plt.legend(handles=patches, ncol=2, **cfg.LEGEND)
    xtick_labels = ["Path %d" % path_id for path_id in range(1, 4)]
    xtick_locations = [l_i for l_i in np.arange(0.2, 1.5, 0.5)]
    plt.xticks(xtick_locations, xtick_labels)

    ytick_locations, ytick_labels = plt.yticks()
    plt.yticks(ytick_locations, [helpers.tick_font(y_i, "%.1f") for y_i in ytick_locations])

    plt.ylabel("Normalized Data Volume", **cfg.AXIS_LABELS)
    helpers.save_figure("per-path-data-volume.pdf", no_legend=True)

def generate_virtual_link_count_plot(results_repository):
    trial_to_virtual_link_counts = {}
    for trial_type in TRIAL_TYPES:
        trial_to_virtual_link_counts[trial_type] = []
        for idx, seed_number in enumerate(SEED_NUMBERS):
            utilization_results, the_vle_trial, end_host_results = read_results(
                    results_repository, trial_type, seed_number)
            number_of_virtual_links = len(the_vle_trial.solver_results.flows)
            trial_to_virtual_link_counts[trial_type].append(number_of_virtual_links)

    data_to_be_plotted = {}
    width = 0.1
    box_offset = (width / 2)
    box_locations = []
    for trial_idx, trial_type in enumerate(TRIAL_TYPES):
        mean_virtual_link_count     = np.mean(trial_to_virtual_link_counts[trial_type])
        virtual_link_count_std_dev  = np.std(trial_to_virtual_link_counts[trial_type])
        box_locations.append(box_offset)
        plt.bar(box_offset, int(mean_virtual_link_count), width, color="blue",
                edgecolor="black", yerr=virtual_link_count_std_dev, ecolor="red",
                capsize=2)
        box_offset += (width + 0.1)

    xtick_locations, xtick_labels = plt.xticks()
    plt.xticks(box_locations, LABEL_NAMES)

    ytick_locations, ytick_labels = plt.yticks()
    plt.yticks(ytick_locations, [helpers.tick_font(int(y_i)) for y_i in ytick_locations])

    plt.ylabel("No. of Admitted VLs", **cfg.AXIS_LABELS)
    helpers.save_figure("virtual-link-counts.pdf", no_legend=True)

def generate_heterogeneous_links_instantaneous_rate_plot():
    link_rate_count = 100
    labels = { (100, 0)         : "\\LARGE{$\\mu=100$, $\\text{CoV}=0.0$}"
             , (100, 50)        : "\\LARGE{$\\mu=100$, $\\text{CoV}=0.5$}"
             , (100, 100)       : "\\LARGE{$\\mu=100$, $\\text{CoV}=1.0$}"
             }

    colors = { (100, 0)         : "red"
             , (100, 50)        : "lime"
             , (100, 100)       : "blue"
             }
    plt.plot(range(link_rate_count), [100 for _ in range(link_rate_count)],
            label=labels[100, 0], color=colors[100, 0])
    for mu, sigma in [(100, 50), (100, 100)]:
        link_rates = heterogeneous_links.get_heterogeneous_link_rates(mu, sigma**2, 
                link_rate_count)
        xs = range(len(link_rates))
        ys = link_rates
        plt.plot(xs, ys, label=labels[mu, sigma], color=colors[mu, sigma])

    plt.rc('font', **cfg.FONT)
    plt.xlim(0, link_rate_count-1)
    plt.xlabel("Time", **cfg.AXIS_LABELS)
    plt.ylabel("Transmission Rate (Mbps)", **cfg.AXIS_LABELS)
    xtick_locations, xtick_labels = plt.xticks()
    ytick_locations, ytick_lables = plt.yticks()
    plt.ylim(0, ytick_locations[-1])
    plt.xticks(xtick_locations[1:], ["" for x_i in xtick_locations])
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i, "%.0f") for y_i in ytick_locations][1:])
    helpers.save_figure("actual-model-tx-rates.pdf", 1, no_legend=False)

def generate_heterogeneous_links_mean_rate_plot():
    link_rate_count = 1000
    number_of_links = 10
    labels = { (100, 0)         : "$\\mu=100$, $\\text{CoV}=0.0$"
             , (100, 50)        : "$\\mu=100$, $\\text{CoV}=0.5$"
             , (100, 100)       : "$\\mu=100$, $\\text{CoV}=1.0$"
             }
    colors = { (100, 0)         : "red"
             , (100, 50)        : "lime"
             , (100, 100)       : "blue"
             }
    
    flow_stats = []
    loc_idx = [idx+1 for idx in range(number_of_links*3)]
    idx = 0
    np.random.shuffle(loc_idx)
    msize = 4.0 
    for _ in range(number_of_links):
        link_rates = [100 for _ in range(link_rate_count)]
        flow_stats.append((np.mean(link_rates), np.std(link_rates), colors[100, 0]))
        plt.errorbar(loc_idx[idx], np.mean(link_rates), yerr=0,
                color=colors[100, 0], capsize=2, linestyle="", marker="D",
                markersize=msize)
        idx += 1

    for mu, sigma in [(100, 50), (100, 100)]:
        for _ in range(number_of_links):
            link_rates = heterogeneous_links.get_heterogeneous_link_rates(mu, sigma**2,
                    link_rate_count)
            flow_stats.append((np.mean(link_rates), np.std(link_rates), colors[mu, sigma]))
            plt.errorbar(loc_idx[idx], np.mean(link_rates), yerr=np.std(link_rates),
                    color=colors[mu, sigma], capsize=2, linestyle="", marker="D",
                    markersize=msize)
            idx += 1
    
    # plot_order = np.random.choice(flow_stats, size=len(flow_stats), replace=False)
    # plot_order = flow_stats
    # np.random.shuffle(plot_order)
    # err     = [p_i[1] for p_i in plot_order]
    # ys      = [p_i[0] for p_i in plot_order]
    # color_list  = [p_i[2] for p_i in plot_order]
    # plt.errorbar(range(len(ys)), ys, yerr=err, linestyle="", marker="D",
    #         capsize=2, c=color_list)

    lines = [matplotlib.lines.Line2D([0], [0], c=c_i, linestyle="", marker="D",
        markersize=msize)
            for c_i in [colors[100, 0], colors[100, 50], colors[100, 100]]]
    legend_labels = [ "\\LARGE{%s}" % labels[100, 0]
                    , "\\LARGE{%s}" % labels[100, 50]
                    , "\\LARGE{%s}" % labels[100, 100]
                    ]
    plt.legend(lines, legend_labels, ncol=1, **cfg.LEGEND)

    plt.rc('font', **cfg.FONT)
    plt.xlim(0, number_of_links*3)
    plt.ylabel("Mean Transmission Rate (Mbps)", **cfg.AXIS_LABELS)
    plt.xlabel("Virtual Links", **cfg.AXIS_LABELS)
    xtick_locations, xtick_labels = plt.xticks()
    ytick_locations, ytick_lables = plt.yticks()
    plt.ylim(0, ytick_locations[-1])
    plt.xticks(xtick_locations[1:], ["" for x_i in xtick_locations][1:])
    plt.yticks(ytick_locations[1:], [helpers.tick_font(y_i, "%.0f") for y_i in ytick_locations][1:])
    helpers.save_figure("mean-model-tx-rates.pdf", 1, no_legend=True)
    
        

def print_mean_and_standard_deviation_of_trace_rates():
    tx_rate_list, mean_flow_tx_rates, std_dev_flow_tx_rates = core_taps.get_rates_for_flows()
    all_rates = [r_i for rate_list in tx_rate_list for r_i in rate_list]
    print("Mu: %f, Sigma: %f" % (np.mean(all_rates), np.std(all_rates)))





































