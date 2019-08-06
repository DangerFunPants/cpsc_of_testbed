
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json
import pprint                       as pp
import pathlib                      as path
import itertools                    as itertools

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


def main():
    utilization_results_path = path.Path("./utilization-results.txt")
    utilization_results = read_utilization_results_from_file(utilization_results_path)
    pp.pprint(utilization_results)











