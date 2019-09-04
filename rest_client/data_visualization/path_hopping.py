
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

import data_visualization.params                as cfg
import data_visualization.helpers               as helpers
import path_hopping.flow_allocation             as flow_allocation

from collections                    import defaultdict
from statistics                     import mean

from data_visualization.helpers     import marker_style, line_style, line_color

FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

# plt.rc("text", usetex=True)
plt.rc("font", **cfg.FONT)
matplotlib.rcParams["xtick.direction"]      = "in"
matplotlib.rcParams["ytick.direction"]      = "in"
# matplotlib.rcParams["text.latex.preamble"]  = [ r"\usepackage{amsmath}"
#                                               , r"\usepackage{amssymb}"
#                                               , r"\usepackage{amsfonts}"
#                                               , r"\usepackage{amsthm}"
#                                               , r"\usepackage{graphics}"
#                                               ]

TRIAL_TYPES     = ["path-hopping"]
LABELS          = ["Path Hopping"]
LABEL_NAMES     = [helpers.trial_name_font(l_i) for l_i in LABELS]
SEED_NUMBERS    = [0xCAFE_BABE, 0xDEAD_BEEF]

def compute_byte_counts_per_time_period(util_results):
    """
    returns a list of dictionaries indexed by the monitoring period. Each dictionary is a map: 
        m_t: source_id -> destination_id -> byte_count
    for all monitoring periods, t.
    """
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
            byte_counts[source_switch][destination_switch] = (results_set["bytesSent"] + 
                    results_set["bytesReceived"])
        byte_counts_per_time_period.append(byte_counts)
    
    util_in_time_period = []
    initial_byte_counts = compute_initial_byte_counts(byte_counts_per_time_period)
    for last_count, current_count in zip(byte_counts_per_time_period, byte_counts_per_time_period[1:]):
        differential_count = subtract_counts(current_count, last_count)
        link_utilization_snapshot = compute_utilization_from_byte_counts(differential_count, 1)
        util_in_time_period.append(link_utilization_snapshot)

    return util_in_time_period

def compute_mean_network_utilization(network_utilization):
    """
    Acts on the output produced by compute_network_utilization_per_time_period. 
    Reduces:
        m_t: source_node -> destination_node -> link_utilization forall. t
    to: 
        m: source_node_destination_node -> mean_link_utilization
    """
    mean_link_utilizations = {}
    for source_node, destination_node in itertools.combinations(network_utilization[0].keys(), 2):
        # mean_link_utilization = np.mean([network_snapshot_at_time_t[source_node][destination_node]
        #     for network_snapshot_at_time_t in network_utilization])
        utilization_over_time = []
        for network_snapshot_at_time_t in network_utilization:
            try:
                utilization_at_time_t = network_snapshot_at_time_t[source_node][destination_node]
            except KeyError:
                continue
            utilization_over_time.append(utilization_at_time_t)
        mean_link_utilizations[source_node, destination_node] = np.mean(utilization_over_time)
    return mean_link_utilizations

def bytes_per_10s_to_mbps(byte_count):
    return (byte_count * 8) / 10**7

def compute_network_utilization_per_time_period(byte_counts_per_time_period, byte_count_to_util_function=bytes_per_10s_to_mbps):
    """
    Acts on the output produced by compute_byte_counts_per_time_period.
    Transforms:
        m_t: source_node -> destination_node -> byte_count forall. t 
    to:
        m_t: source_node -> destination_node -> link_utilization forall. t

    by applying byte_count_to_util_function to all of the byte_count_{t,s,d} forall. t, s, d

    The default byte_count_to_util_function maps from a byte_count taken over a period of 10s
    to Mbps.
    """
    network_utilization_per_time_period = []
    for byte_counts_at_time_t in byte_counts_per_time_period:
        utilization_at_time_t = {}
        for source_node, destination_node_to_byte_count in byte_counts_at_time_t.items():
            utilization_at_time_t[source_node] = {}
            for destination_node, byte_count in destination_node_to_byte_count.items():
                utilization_at_time_t[source_node][destination_node] = byte_count_to_util_function(byte_count)
        network_utilization_per_time_period.append(utilization_at_time_t)
    return network_utilization_per_time_period

def read_results(results_repository, provider_name):
    schema_variables = { "provider-name"   : provider_name
                       }
    # results = results_repository.read_trial_results(schema_variables, files)
    trial_provider = results_repository.read_trial_provider(schema_variables)
    for trial in trial_provider:
        return trial.get_parameter("utilization-results"), trial.get_parameter("flow-set")

def generate_link_utilization_cdf(results_repository, provider_name):
    """
    Generate a CDF of mean link utilization
    """
    trial_provider = results_repository.read_trial_provider(provider_name)
    
    for idx, trial in enumerate(trial_provider):
        # print(trial)
        utilization_results = trial.get_parameter("utilization-results")

        byte_counts_per_time_period         = compute_byte_counts_per_time_period(utilization_results)
        network_utilization_per_time_period = compute_network_utilization_per_time_period(
                byte_counts_per_time_period)
        mean_network_utilization            = compute_mean_network_utilization(
                network_utilization_per_time_period)

        pp.pprint(mean_network_utilization)

        link_utilizations = sorted(mean_network_utilization.values())
        xs = [0.0]
        ys = [0.0]
        for ctr, link_utilization in enumerate(link_utilizations):
            xs.append(link_utilization)
            ys.append(ctr / len(link_utilizations))
        plt.plot(xs, ys, marker=helpers.marker_style(idx), color=helpers.line_color(idx), 
                linestyle=helpers.line_style(idx), label="K=%d" % trial.get_parameter("K"))
    
    plt.xlabel("Link throughput (Mbps)")
    plt.ylabel("P{x < X}")
    plt.legend(**cfg.LEGEND)
    helpers.save_figure("%s-cdf.pdf" % provider_name, no_legend=True)

def generate_topo_utilization_graph(results_repository, provider_name):
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

    trial_provider = results_repository.read_trial_provider(provider_name)
    the_trial = next(iter(trial_provider))
    utilization_results = the_trial.get_parameter("utilization-results")
    net_topo = generate_graph_from_utilization_results(utilization_results)
    # seed_number = rand.randint(0, 2**32)
    seed_number = 1107035453
    layout = lambda g: nx.circular_layout(g)
    byte_counts_per_time_period         = compute_byte_counts_per_time_period(utilization_results)
    network_utilization_per_time_period = compute_network_utilization_per_time_period(
            byte_counts_per_time_period)
    mean_utils                          = compute_mean_network_utilization(
            network_utilization_per_time_period)

    cs = []
    max_utilization_value = 1000 # max(mean_utils.values())
    color_map_name = "coolwarm"
    cm = plt.get_cmap(color_map_name)
    plt.set_cmap(color_map_name)
    for (u, v) in net_topo.edges():
        if (u, v) in mean_utils:
            u_val = mean_utils[u, v]
        else:
            u_val = mean_utils[v, u]
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
    helpers.save_figure("%s-topo-util.pdf" % provider_name, no_legend=True)
    plt.clf()
    pp.pprint(min(mean_utils.values()))
    print(seed_number)


def generate_link_utilization_box_plot(results_repository, provider_name):
    """
    Generate a box and whisker plot showing the utilization of all the links in the 
    network for a set of trials.
    """
    trial_provider = results_repository.read_trial_provider(provider_name)
    link_utilization_results_for_trials = []
    x_axis_labels = []
    for idx, trial in enumerate(trial_provider):
        utilization_results = trial.get_parameter("utilization-results")
        byte_counts_per_time_period = compute_byte_counts_per_time_period(utilization_results)
        network_utilization_per_time_period = compute_network_utilization_per_time_period(
                byte_counts_per_time_period)
        mean_network_utilization = compute_mean_network_utilization(
                network_utilization_per_time_period)
        link_utilization_results_for_trials.append(list(mean_network_utilization.values()))
        x_axis_labels.append("K=%d" % trial.get_parameter("K"))


    bp = plt.boxplot(link_utilization_results_for_trials, labels=x_axis_labels,
            whiskerprops={"linestyle": "--"},
            flierprops={"marker":"x", "markerfacecolor": "red", "markeredgecolor": "red"})
    for element in ["boxes"]:
        plt.setp(bp[element], color="blue")

    plt.setp(bp["medians"], color="red")

    plt.ylabel("Link Throughput (Mbps)")
    helpers.save_figure("%s-box-plot.pdf" % provider_name, 3, no_legend=True)
        



















