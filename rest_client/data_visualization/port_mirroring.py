
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json 
import pprint                       as pp
import pathlib                      as path
import pygraphviz                   as pgv
import itertools                    as itertools

import nw_control.topo_mapper           as topo_mapper
import nw_control.util                  as util
import data_visualization.params        as cfg
import data_visualization.helpers       as helpers
import port_mirroring.params            as pm_cfg
import trials.port_mirroring_trial      as port_mirroring_trial

from collections                    import defaultdict
from statistics                     import mean

def save_figure(figure_name, **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    plt.savefig(str(p), **kwargs)
    plt.clf()

def read_results(results_repository, provider_name, solution_name, trial_name):
    schema_variables = { "provider-name"        : provider_name
                       , "solution-type"        : solution_name
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
    switches            = port_mirroring_trial.PortMirroringSwitch.deserialize(results["switches"])
    utilization_json    = helpers.read_json_response(results["utilization-results.txt"])
    net_utilization     = helpers.compute_network_util_over_time(utilization_json)
    ports               = port_mirroring_trial.PortMirroringPorts.deserialize(results["ports"])
    return topo, flows, switches, solutions, net_utilization, ports

def compute_theoretical_mirroring_rates_for_switches(switches, solutions):
    rates_for_switch = defaultdict(float)
    for switch_id, solutions in solutions.items():
        for solution in solutions:
            mirrored_port_rate = switches[solution.mirror_switch_id].rate_for_port(
                    solution.mirror_switch_port)
            rates_for_switch[solution.mirror_switch_id] += mirrored_port_rate
    return rates_for_switch

def compute_most_used_mirroring_port(switches, solutions):
    rates_for_switch = compute_theoretical_mirroring_rates_for_switches(switches, solutions)
    max_mirroring_port_switch_id = max(rates_for_switch.items(), key=lambda kvp: kvp[1])
    max_port_rate = compute_most_used_mirroring_port_rate(switches, solutions)
    # if max_mirroring_port_switch_id[1] != max_port_rate:
    #     pp.pprint({k: str(v) for k, v in switches.items()})
    #     pp.pprint({k: str(v) for k, v in solutions.items()})
    #     raise ValueError("Max port rates don't match %f and %f. Max node Id %d" % 
    #             (max_mirroring_port_switch_id[1], max_port_rate, max_mirroring_port_switch_id[0]))
    #     print("max port rates don't match, computed %f, actual %f." %
    #             (max_mirroring_port_switch_id[1], max_port_rate))
    return max_mirroring_port_switch_id[0]

def compute_most_used_mirroring_port_rate(switches, solutions):
    # rates_for_switch = compute_theoretical_mirroring_rates_for_switches(switches, solutions)
    # return max(rates_for_switch.items(), key=lambda kvp: kvp[1])[1]
    return next(iter(solutions.values()))[0].objective_value

def compute_theoretical_and_actual_utilization(results_repository):
    utilization_data = defaultdict(lambda: defaultdict(list))
    theoretical_data = defaultdict(dict)

    for run in ["run-%d" % run_idx for run_idx in range(0, 1)]:
        for solution_name in ["rnd", "det", "df", "greedy", "optimal"]:
            for trial_name in ["sub-trial-%d" % trial_idx for trial_idx in range(5)]:
                topo, flows, switches, solutions, net_utilization, ports = read_results(
                        results_repository, run, solution_name, trial_name)

                most_used_mirroring_port = compute_most_used_mirroring_port(switches, solutions)

                id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
                mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
                collector_switch_dpid = topo_mapper.get_collector_switch_dpid()

                mirror_port_utils = []
                for util_at_time_t in net_utilization:
                    try:
                        mirror_port_utils.append(
                                util_at_time_t[mirror_port_dpid][collector_switch_dpid])
                    except KeyError as ke:
                        print("KEY ERROR KE %s" % ke)

                theoretical_util = compute_most_used_mirroring_port_rate(switches, solutions)
                utilization_data[solution_name][len(flows)].extend(mirror_port_utils)
                theoretical_data[solution_name][len(flows)] = theoretical_util

    return utilization_data, theoretical_data

def compute_theoretical_and_actual_mean_utilization(results_repository):
    def reduce_to_mean(results_dict):
        mean_dict = defaultdict(dict)
        for solution_name, flow_count_to_util_list in results_dict.items():
            for flow_count, util_list in flow_count_to_util_list.items():
                mean_dict[solution_name][flow_count] = mean(util_list)
        return mean_dict

    utilization_data, theoretical_data = compute_theoretical_and_actual_utilization(
            results_repository)
    return reduce_to_mean(utilization_data), theoretical_data

def compute_actual_std_deviation(results_repository):
    utilization_data, _ = compute_theoretical_and_actual_utilization(results_repository)
    std_dev_map = defaultdict(dict)
    for solution_name, flow_count_to_data_list in utilization_data.items():
        for flow_count, data_list in flow_count_to_data_list.items():
            std_dev_map[solution_name][flow_count] = np.std(data_list)

    sorted_dev_map = {}
    for solution_name, flow_count_to_std_dev in std_dev_map.items():
        tuple_list = []
        for flow_count, std_dev in flow_count_to_std_dev.items():
            tuple_list.append((flow_count, std_dev))
        sorted_dev_map[solution_name] = [util.bytes_per_second_to_mbps(t[1]) for t in sorted(tuple_list, key=lambda kvp: kvp[0])]
    return sorted_dev_map

def generate_max_mirror_port_utilization_bar_plot(results_repository):
    utilization_data, _     = compute_theoretical_and_actual_mean_utilization(results_repository)
    actual_std_deviation    = compute_actual_std_deviation(results_repository)

    width = 0.15
    ind = np.arange(1, 6)
    fig, ax = plt.subplots()
    labels          = ["rnd", "det", "df", "greedy", "optimal"]
    legend_labels   = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    half            = len(labels) // 2
    bar_locations   = [w for w in np.arange((width/2), len(labels)*width, width)]
    print(bar_locations)
    colors          = ["red", "green", "blue", "orange", "purple"]
    hatch           = ["//", "\\", "//", "\\", "//"]
    for bar_idx, solution_name in enumerate(labels):
        data_tuples = sorted([(k, v) for k, v in utilization_data[solution_name].items()],
                key=lambda kvp: kvp[0])
        yerr_values = actual_std_deviation[solution_name]
        xs = [flow_count for flow_count, _ in data_tuples]
        ys = [util.bytes_per_second_to_mbps(data) 
                for _, data in data_tuples]
        ax.bar(ind+bar_locations[bar_idx], ys, width, color=colors[bar_idx], hatch=hatch[bar_idx],
                label=legend_labels[bar_idx], yerr=yerr_values, align="center",
                ecolor="black")
    
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.xticks(ind+(width*len(labels))/2, ind*10)
    plt.grid()
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
            shadow=True, ncol=len(labels))

    helpers.save_figure("pm-plot-one.pdf")

def generate_theoretical_vs_actual_utilization_bar_plot(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(
            results_repository)
    actual_std_deviation = compute_actual_std_deviation(results_repository)

    width           = 0.35
    labels          = ["rnd", "det", "df", "greedy", "optimal"]
    legend_labels   = ["\\epsilon-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    colors          = ["orange", "green", "skyblue", "purple", "yellow"]
    hatch           = ["//", "\\", "//", "\\", "//"]

    for solution_name in labels:
        ind = np.arange(1, 6)
        fig, ax = plt.subplots()
        data_tuples = sorted([(k, v) for k, v in utilization_data[solution_name].items()],
                key=lambda kvp: kvp[0])
        yerr_values = actual_std_deviation[solution_name]
        xs = [flow_count for flow_count, _ in data_tuples]
        ys = [util.bytes_per_second_to_mbps(data) for _, data in data_tuples]
        ax.bar(ind-(width/2), ys, width, color="green", hatch="\\", 
                tick_label=xs, label="Measured", yerr=yerr_values, ecolor="black")

        theoretical_tuples = sorted([(k, v) for k, v in theoretical_data[solution_name].items()],
                key=lambda kvp: kvp[0])
        xs = [flow_count for flow_count, _ in theoretical_tuples]
        ys = [util_val * pm_cfg.rate_factor for _, util_val in theoretical_tuples]
        ax.bar(ind+(width/2), ys, width, color="skyblue", hatch=".", 
                tick_label=xs, label="Expected")
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel("Number of Flows")
        plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
        plt.grid()
        plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
                shadow=True, ncol=len(labels))
        save_figure("plot-two-%s.pdf" % solution_name)

def generate_theoretical_vs_actual_compact_bar_plot(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(
            results_repository)
    # utilization_data, theoretical_data = compute_theoretical_and_actual_utilization(
    #         results_repository)
        

    actual_std_deviation = compute_actual_std_deviation(results_repository)

    width           = 0.15
    ind             = np.arange(1, 6)
    fig, ax         = plt.subplots()
    labels          = ["rnd", "det", "df", "greedy", "optimal"]
    half            = len(labels)//2
    legend_labels   = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    colors          = ["red", "green", "blue", "orange", "purple"]
    alt_colors      = ["blue", "red", "purple", "green", "orange"]
    hatch           = ["//", "\\", "//", "\\", "//"]
    bar_locations   = [w for w in np.arange((width/2), len(labels)*width, width)]

    for bar_idx, solution_name in enumerate(labels):
        data_tuples = sorted([(k, v) for k, v in utilization_data[solution_name].items()],
                key=lambda kvp: kvp[0])
        theoretical_tuples = sorted([(k, v) for k, v in theoretical_data[solution_name].items()],
                key=lambda kvp: kvp[0])

        yerr_values = actual_std_deviation[solution_name]
        xs = [flow_count for flow_count, _ in data_tuples]
        measured_ys = [util.bytes_per_second_to_mbps(data)
                for _, data in data_tuples]
        theoretical_ys = [util_val * pm_cfg.rate_factor
                for _, util_val in theoretical_tuples]
        theoretical_ys = [abs(theoretical_ys[idx] - measured_ys[idx])
                for idx in range(len(theoretical_ys))]

        ax.bar(ind+bar_locations[bar_idx], theoretical_ys, width, color=colors[bar_idx], 
                hatch=hatch[bar_idx], label=legend_labels[bar_idx],
                align="center", ecolor="black")
    
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.xticks(ind+(width*len(labels))/2, ind*10)
    plt.grid()
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
            shadow=True, ncol=len(labels))

    helpers.save_figure("pm-plot-two.pdf")

def generate_mirroring_port_utilization_bar_plot(results_repository):
    labels          = ["rnd", "det", "df", "greedy", "optimal"]
    legend_labels   = ["\\epsilon-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    trial_name      = "sub-trial-4"
    run_name        = "run-0"
    for solution_name in labels:
        topo, flows, switches, solutions, link_utilization_data, ports = read_results(
                results_repository, run_name, solution_name, trial_name)
        link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
        mean_utils      = []
        labels          = []
        errors          = []
        collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
        id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
        dpid_to_id = {v: k for k, v in id_to_dpid.items()}
        for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
            link_utils_over_time = []
            for time_idx, net_snapshot in enumerate(link_utilization_data):
                try:
                    link_utils_over_time.append(net_snapshot[s][d])
                except KeyError:
                    print("net_snapshot at time %d did not contain link %s -> %s" % 
                            (time_idx, s, d))
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

        mirroring_utils = compute_theoretical_mirroring_rates_for_switches(switches, solutions)
        ys = []
        xs = []
        for switch_id in switches.keys():
            aggregate_rate = mirroring_utils[switch_id]
            xs.append(switch_id)
            ys.append(aggregate_rate * pm_cfg.rate_factor)
        ax.bar(ind+(width/2), ys, width, color="green", hatch="\\", label="Expected") 

        plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
                shadow=True, ncol=2)
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel("Switch ID")
        plt.ylabel("Mean Mirroring Port Rate ($\\frac{Mb}{s}$)")
        plt.grid()
        save_figure("plot-three-%s.pdf" % solution_name)
        plt.clf()

def generate_port_mirroring_port_utilization_cdf(results_repository):
    labels          = ["rnd", "det", "df", "greedy", "optimal"]
    legend_labels   = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    markers         = ["^", "*", "^", "o", "x"]
    colors          = ["red", "green", "blue", "orange", "purple"]
    trial_name      = "sub-trial-4"
    run_name        = "run-0"
    for solution_idx, solution_name in enumerate(labels):
        topo, flows, switches, solutions, link_utilization_data, ports = read_results(
                results_repository, run_name, solution_name, trial_name)
        link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
        mean_utils      = []
        labels          = []
        errors          = []
        collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
        id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
        dpid_to_id = {v: k for k, v in id_to_dpid.items()}
        for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
            link_utils_over_time = []
            for time_idx, net_snapshot in enumerate(link_utilization_data):
                try:
                    link_utils_over_time.append(net_snapshot[s][d])
                except KeyError:
                    print("net_snapshot at time %d did not contain link %s -> %s" % 
                            (time_idx, s, d))
            mean_utils.append(util.bytes_per_second_to_mbps(mean(link_utils_over_time)))
            errors.append(util.bytes_per_second_to_mbps(np.std(link_utils_over_time)))
            labels.append(dpid_to_id[s])
    
        cdf_data = sorted(mean_utils)
        xs = [0.0]
        ys = [0.0]
        for idx, d in enumerate(cdf_data):
            xs.append(d)
            ys.append((1 + idx) / len(cdf_data))
        
        plt.plot(xs, ys, label=legend_labels[solution_idx], marker=markers[solution_idx],
                color=colors[solution_idx])
        plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
                shadow=True, ncol=len(labels))
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.grid()
        plt.xlabel("Mirroring Port Rate $\\frac{Mb}{s}$")
        plt.ylabel("$\\mathbb{P}\\{x < \\mathcal{X}\\}$")

    save_figure("pm-plot-three-cdf.pdf")

def generate_theoretical_util_graph(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(
            results_repository)

    width = 0.2
    ind = np.arange(1, 6)
    fig, ax = plt.subplots()
    labels          = ["det", "df", "greedy", "optimal", "rnd"]
    half            = len(labels) // 2
    bar_locations   = [w for w in np.arange((width/2), len(labels)*width, width)]
    colors          = ["green", "skyblue", "purple", "yellow"]
    hatch           = ["\\", "//", "\\", "//"]

    for bar_idx, solution_name in enumerate(labels):
        theoretical_tuples = sorted([(k, v) for k, v in theoretical_data[solution_name].items()],
                key=lambda kvp: kvp[0])
        xs = [flow_count for flow_count, _ in theoretical_tuples]
        ys = [util_val * pm_cfg.rate_factor for _, util_val in theoretical_tuples]
        ax.bar(ind+bar_locations[bar_idx], ys, width, color=colors[bar_idx], hatch=hatch[bar_idx], 
                label=labels[bar_idx])

    
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.grid()
    plt.xticks(ind+0.4, ind*10)
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
            shadow=True, ncol=len(labels))

    helpers.save_figure("pm-plot-four.pdf")

def generate_mirror_port_rate_difference_file(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(
            results_repository)
    
    labels          = ["det", "df", "greedy", "optimal", "rnd"]
    difference_map = defaultdict(dict)
    for solution_type_a, solution_type_b in itertools.product(labels, repeat=2):
        for flow_count in range(10, 60, 10):
            data_a = util.bytes_per_second_to_mbps(utilization_data[solution_type_a][flow_count])
            data_b = util.bytes_per_second_to_mbps(utilization_data[solution_type_b][flow_count])
            difference = data_a - data_b
            difference_map[(solution_type_a, solution_type_b)][flow_count] = difference

    pp.pprint(dict(difference_map))

def generate_port_mirroring_port_utilization_compact_bar_plot(results_repository):
    solution_labels     = ["rnd", "det", "df", "greedy", "optimal"]
    legend_labels       = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    markers             = ["^", "*", "^", "o", "x"]
    colors              = ["red", "green", "blue", "orange", "purple"]
    trial_name          = "sub-trial-4"
    run_name            = "run-0"
    width               = 0.15
    legend_labels       = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
    hatch               = ["//", "\\", "//", "\\", "//"]
    bar_locations       = [w for w in np.arange((width/2), len(solution_labels)*width, width)]
    ind                 = np.arange(11)
    fig, ax             = plt.subplots()

    for bar_idx, solution_name in enumerate(solution_labels):
        topo, flows, switches, solutions, link_utilization_data, ports = read_results(
                results_repository, run_name, solution_name, trial_name)
        link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
        mean_utils      = []
        labels          = []
        errors          = []
        collector_switch_dpid = topo_mapper.get_collector_switch_dpid()
        id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
        dpid_to_id = {v: k for k, v in id_to_dpid.items()}
        for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
            link_utils_over_time = []
            for time_idx, net_snapshot in enumerate(link_utilization_data):
                try:
                    link_utils_over_time.append(net_snapshot[s][d])
                except KeyError:
                    print("net_snapshot at time %d did not contain link %s -> %s" % 
                            (time_idx, s, d))
            mean_utils.append(util.bytes_per_second_to_mbps(mean(link_utils_over_time)))
            errors.append(util.bytes_per_second_to_mbps(np.std(link_utils_over_time)))
            labels.append(dpid_to_id[s])
        
        ys = sorted(zip(labels, mean_utils), key=lambda kvp: kvp[0])
        ys = [y_i[1] for y_i in ys]
        ax.bar(ind+bar_locations[bar_idx], ys, width, color=colors[bar_idx], hatch=hatch[bar_idx],
                label=legend_labels[bar_idx], align="center")
                # ecolor="black", yerr=yerr_values)

    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel("Switch ID")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.xticks(ind+((width*len(solution_labels))/2), ind+1)
    plt.grid()
    plt.xlim(0, 10+(width*len(solution_labels)))
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
            shadow=True, ncol=len(solution_labels))

    helpers.save_figure("pm-plot-three-compact-bar.pdf")







