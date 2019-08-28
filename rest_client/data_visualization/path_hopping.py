
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

def read_results(results_repository, trial_type, seed_number):
    schema_variables = { "trial-type"   : trial_type
                       , "seed-number"  : str(seed_number)
                       }
    files = [ "utilization-results.txt"
            , "flows.json"
            ]
    results = results_repository.read_trial_results(schema_variables, files)

    flows               = flow_allocation.parse_flows_from_json(results["flows.json"])
    utilization_results = [net_snapshot["netUtilStats"]["utilizationStats"]
            for net_snapshot in json.loads(results["utilization-results.txt"])]

    return utilization_results, flows

def generate_link_utilization_cdf(results_repository):
    utilization_results, flows = read_results(results_repository, "path-hopping",
            SEED_NUMBERS[1])
    
    byte_counts_per_time_period         = compute_byte_counts_per_time_period(utilization_results)
    network_utilization_per_time_period = compute_network_utilization_per_time_period(
            byte_counts_per_time_period)
    mean_network_utilization            = compute_mean_network_utilization(
            network_utilization_per_time_period)

    link_utilizations = sorted(mean_network_utilization.values())
    xs = [0.0]
    ys = [0.0]
    for ctr, link_utilization in enumerate(link_utilizations):
        xs.append(link_utilization)
        ys.append(ctr / len(link_utilizations))
    
    plt.plot(xs, ys, **cfg.BASIC_CDF_PARAMS)
    helpers.save_figure("path-hopping-cdf.pdf", no_legend=True)






















