
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json 
import pprint                       as pp
import pathlib                      as path
import pygraphviz                   as pgv

import nw_control.topo_mapper           as topo_mapper
import nw_control.util                  as util
import data_visualization.params        as cfg
import data_visualization.helpers       as helpers
import port_mirroring.params            as pm_cfg
import trial.port_mirroring_trial       as port_mirroring_trial

from collections                    import defaultdict
from statistics                     import mean

def save_figure(figure_name, **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    plt.savefig(str(p), **kwargs)
    plt.clf()

def read_results(results_repository, provider_name, solution_name, trial_name):
    schema_variables = { "provider-name"        : provider_name
                       , "solution-name"        : solution_name
                       , "trial-name"           : trial_name    
                       }
    files = [ "utilization-results.txt"
            , "topo"
            , "flows"
            , "switches"
            , "solutions"
            , "ports"
            ]
    results = results_repository.read_trial_results(schema_variables, files)
    topo                = results["topo"]
    flows               = port_mirroring_trial.PortMirroringFlow.deserialize(results["flows"])
    solutions           = port_mirroring_trial.PortMirroringSolution.deserialize(results["solutions"])
    utilization_json    = read_json_response(results["utilization-results.txt"])
    net_utilization     = compute_network_util_over_time(utilization_json)
    return topo, flows, solutions, net_utilization, ports

def compute_theoretical_and_actual_utilization(results_repository):
    utilization_data = defaultdict(lambda: defaultdict(list))
    theoretical_data = defaultdict(lambda: defaultdict(list))

    for run in ["run-%d" % run_idx for run_idx in range(3)]:
        for solution_name in ["det", "df", "greedy", "optimal"]:
            for trial_name in ["sub-trial-%d" % trial_idx in range(5)]:
                topo, flows, solutions, net_utilization, ports = read_results(results_repository,
                        run, solution_name, trial_name)

                most_used_mirroring_port = helpers.compute_most_used_mirroring_port(flows, 
                        solutions)

            id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
            mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
            collector_switch_dpid = topo_mapper.get_collector_switch_dpid()

            mirror_port_utils = [util_at_time_t[mirror_port_dpid][collector_switch_dpid]
                for util_at_time_t in net_utilization]
            theoretical_util = compute_theoretical_util(flows, solutions)
            utilization_data[run][solution_name][len(flows)].extend(mirror_port_utils)
            theoretical_data[run][solution_name][len(flows)].append(theoretical_util)

def compute_theoretical_and_actual_mean_utilization(results_repository):
    def reduce_to_mean(results_dict):
        mean_dict = defaultdict(dict)
        for solution_name, flow_count_to_util_list in results_dict.items():
            for flow_count, util_list in flow_count_to_util_list.items():
                mean_dict[solution_name][flow_count] = mean(util_list)

    utilization_data = defaultdict(lambda: defaultdict(list))
    theoretical_data = defaultdict(lambda: defaultdict(list))

    for run in ["run-%d" % run_idx for run_idx in range(3)]:
        for solution_name in ["det", "df", "greedy", "optimal"]:
            for trial_name in ["sub-trial-%d" % trial_idx in range(5)]:
                topo, flows, solutions, net_utilization, ports = read_results(results_repository,
                        run, solution_name, trial_name)

                most_used_mirroring_port = helpers.compute_most_used_mirroring_port(flows, 
                        solutions)

            id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
            mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
            collector_switch_dpid = topo_mapper.get_collector_switch_dpid()

            mirror_port_utils = [util_at_time_t[mirror_port_dpid][collector_switch_dpid]
                for util_at_time_t in net_utilization]
            theoretical_util = compute_theoretical_util(flows, solutions)
            utilization_data[solution_name][len(flows)].extend(mirror_port_utils)
            theoretical_data[solution_name][len(flows)].append(theoretical_util)

    return reduce_to_mean(utilization_data), reduct_to_mean(theoretical_data)

def generate_max_mirror_port_utilization_bar_plot(results_repository):
    utilization_data, _ = compute_theoretical_and_actual_mean_utilization(results_repository)
    actual_error        = compute_theoretical_and_actual_error(results_repository)

    
    







