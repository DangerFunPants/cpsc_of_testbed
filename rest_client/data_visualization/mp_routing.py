
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json
import pprint                       as pp
import pathlib                      as path
import itertools                    as itertools

import mp_routing.vle_trial         as vle_trial

from collections                    import defaultdict
from statistics                     import mean

FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

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
            # byte_counts[source_switch][destination_switch] = results_set["packetsSent"] + results_set["packetsReceived"]
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
    xs = np.arange(len(ys))
    plt.bar(xs, ys)
    save_figure("link-util.pdf")
    plt.clf()

def read_results(results_repository, trial_type, trial_name):
    schema_variables = { "trial-name"   : trial_name
                       , "trial-type"   : trial_type
                       }

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

def generate_link_utilization_bar_plot(results_repository):
    utilization_results, the_vle_trial, end_host_results = read_results(results_repository, "link-embedding",
            "test-trial")
    link_utilization_data = compute_network_util_over_time(utilization_results)
    graph_link_utilization(link_utilization_data)

def generate_loss_rates(results_repository):
    utilization_results, the_vle_trial, end_host_results = read_results(results_repository, "link-embedding",
            "test-trial")
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
    print(max(all_loss_rates))











