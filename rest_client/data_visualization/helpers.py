import matplotlib
matplotlib.use("Agg")

import data_visualization.params        as cfg

import matplotlib.pyplot                as plt
import json                             as json

from collections import defaultdict

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
