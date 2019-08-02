
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot                as plt
import networkx                         as nx
import numpy                            as np
import json                             as json 
import pprint                           as pp
import pathlib                          as path
import pygraphviz                       as pgv

import nw_control.topo_mapper           as topo_mapper
import nw_control.util                  as util
import data_visualization.params        as cfg
import data_visualization.helpers       as helpers
import port_mirroring.params            as pm_cfg

from collections                    import defaultdict
from statistics                     import mean

from trials.flow_mirroring_trial    import FlowDefinition, SolutionDefinition, SwitchDefinition
from data_visualization.helpers     import read_json_response_from_file, compute_initial_byte_counts, subtract_counts, compute_utilization_from_byte_counts, compute_network_util_over_time, read_json_response

SOLUTION_LABELS         = { "approx": "BiSec"
                          , "optimal": "Optimal"
                          }
SOLUTION_NAMES          = ["approx", "optimal"]

def compute_most_used_mirroring_port(flows, solutions):
    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    return max(mirroring_utils.items(), key=lambda t: t[1])[0]

def compute_most_used_mirroring_port_rate(flows, solutions):
    mirroring_utils = defaultdict(float)
    for flow in flows.values():
        mirroring_switch_for_flow = solutions[flow.flow_id].mirror_switch_id
        mirroring_utils[mirroring_switch_for_flow] += flow.traffic_rate

    return max(mirroring_utils.items(), key=lambda t: t[1])[1] 

def read_results(results_repository, provider_name, solution_type, trial_name):
    schema_variables = { "provider-name"        : provider_name
                       , "solution-type"        : solution_type
                       , "trial-name"           : trial_name    
                       }
    files = [ "utilization-results.txt"
            , "flows"
            , "switches"
            , "solutions"
            , "topo"
            ]
    results = results_repository.read_trial_results(schema_variables, files)
    topo                = results["topo"]
    flows               = FlowDefinition.deserialize(results["flows"])
    switches            = SwitchDefinition.deserialize(results["switches"])
    solutions           = SolutionDefinition.deserialize(results["solutions"])
    utilization_json    = read_json_response(results["utilization-results.txt"])
    net_utilization     = compute_network_util_over_time(utilization_json)
    return topo, flows, switches, solutions, net_utilization

# compute_theoretical_and_actual_utilization :: 
#     results_repository ->
#     run_count ->
#     solution_names ->
#     trial_count ->
#     (solution_name -> flow_count -> util_list)
def compute_theoretical_and_actual_utilization( results_repository
                                              , run_count
                                              , solution_names
                                              , trial_count):
    utilization_data = defaultdict(lambda: defaultdict(list))
    theoretical_data = defaultdict(lambda: defaultdict(list))

    for run in ["run-%d" % run_idx for run_idx in range(run_count)]:
        for solution_name in solution_name:
            for trial_name in ["sub-trial-%d" % trial_idx for trial_idx in range(trial_count)]:
                topo, flows, switches, solutions, net_utilization = read_results(
                        results_repository, run, solution_name, trial_name)

                most_used_mirroring_port = compute_most_used_mirroring_port(flows, solutions)

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
                theoretical_data[solution_name][len(flows)].append(theoretical_util)

    return utilization_data, theoretical_data

def compute_theoretical_and_actual_mean_utilization( results_repository
                                                   , run_count
                                                   , solution_names
                                                   , trial_count):
    def reduce_to_mean(results_dict):
        mean_dict = defaultdict(dict)
        for solution_name, flow_count_to_util_list in results_dict.items():
            for flow_count, util_list in flow_count_to_util_list.items():
                mean_dict[solution_name][flow_count] = mean(util_list)
        return mean_dict

    utilization_data, theoretical_data = compute_theoretical_and_actual_utilization(
            results_repository, run_count, solution_names, trial_count)
    return reduce_to_mean(utilization_data), reduce_to_mean(theoretical_data)

# compute_theoretical_and_actual_utilization_by_run ::
#     results_repository  ->
#     run_count           ->
#     solution_names      ->
#     trial_count         ->
#     (run_name -> solution_name -> flow_count -> util_list)
def compute_theoretical_and_actual_utilization_by_run( results_repository
                                                     , run_count
                                                     , solution_names
                                                     , trial_count):
    utilization_data = {}
    theoretical_data = {}
    
    for run in ["run-%d" % run_idx for run_idx in range(run_count)]:
        solution_results                = {}
        theoretical_solution_results    = {}
        for solution_name in solution_names:
            trial_results                   = {}
            theoretical_trial_results       = {}
            for trial_name in ["sub-trial-%d" % trial_idx for trial_idx in range(trial_count)]:
                topo, flows, switches, solutions, net_utilization = read_results(
                        results_repository, run, solution_name, trial_name)

                most_used_mirroring_port = compute_most_used_mirroring_port(flows, solutions)

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

                theoretical_util = compute_most_used_mirroring_port_rate(flows, solutions)
                trial_results[len(flows)] = mirror_port_utils
                theoretical_trial_results[len(flows)] = theoretical_util

            solution_results[solution_name]                 = trial_results
            theoretical_solution_results[solution_name]     = theoretical_trial_results

        utilization_data[run] = solution_results
        theoretical_data[run] = theoretical_solution_results

    return utilization_data, theoretical_data

def generate_max_mirror_port_utilization_bar_plot(results_repository):
    # utilization_data, _     = compute_theoretical_and_actual_mean_utilization(results_repository)
    # actual_error            = compute_theoretical_and_actual_error(results_repository)

    run_count           = 3
    solution_names      = ["approx", "optimal"]
    trial_count         = 5
    utilization_data, _ = compute_theoretical_and_actual_utilization_by_run(
            results_repository, run_count, solution_names, trial_count)

    # mean_util_lists :: solution_name -> flow_count -> [util_vals]
    mean_util_lists = defaultdict(lambda: defaultdict(list))
    for run_name, solution_name_to_flow_count in utilization_data.items():
        for solution_name, flow_count_to_util_list in solution_name_to_flow_count.items():
            for flow_count, util_list in flow_count_to_util_list.items():
                mean_util_value = util.bytes_per_second_to_mbps(mean(util_list[1:]))
                mean_util_lists[solution_name][flow_count].append(mean_util_value)

    # std_deviations :: solution_name -> flow_count -> std_dev
    std_deviations      = defaultdict(dict)
    # mean_utils :: solution_name -> flow_count -> mean_util
    mean_utils          = defaultdict(dict)
    for solution_name, flow_count_to_util_list in mean_util_lists.items():
        for flow_count, util_list in flow_count_to_util_list.items():
            std_deviations[solution_name][flow_count] = np.std(util_list)
            mean_utils[solution_name][flow_count] = mean(util_list)
    pp.pprint(mean_utils)

    width           = 0.35
    ind             = np.arange(1, 6)
    fig, ax         = plt.subplots()
    labels          = SOLUTION_LABELS
    half            = len(labels) // 2
    bar_locations   = [w for w in np.arange((width/2), len(labels)*width, width)]
    colors          = cfg.BAR_PLOT_COLORS
    hatch           = cfg.BAR_PLOT_TEXTURES
    for bar_idx, solution_name_to_flow_count in enumerate(mean_utils.items()):
        solution_name, flow_count_to_mean_util = solution_name_to_flow_count
        data_tuples = sorted([(flow_count, util_val)
            for flow_count, util_val in flow_count_to_mean_util.items()],
            key=lambda kvp: kvp[0])
        yerr_tuples = sorted([(flow_count, std_dev)
            for flow_count, std_dev in std_deviations[solution_name].items()],
            key=lambda kvp: kvp[0])

        xs = [d_i[0] for d_i in data_tuples]
        ys = [d_i[1] for d_i in data_tuples]
        yerr_values = [s_i[1] for s_i in yerr_tuples]
        ax.bar(ind+bar_locations[bar_idx], ys, width, color=colors[bar_idx], hatch=hatch[bar_idx],
                label=labels[solution_name], yerr=yerr_values, align="center",
                ecolor="black")

    plt.rc('text', usetex=True)
    plt.rc('font', **cfg.FONT)
    plt.grid(**cfg.GRID)
    plt.xticks(ind+(width*len(labels))/2, ind*10)
    plt.xlabel("Number of Flows", **cfg.AXIS_LABELS)
    plt.ylabel("Maximum switch load (Mbps)", **cfg.AXIS_LABELS)
    # plt.legend(ncol=2, **cfg.LEGEND)
    helpers.save_figure("sfm-objective.pdf", 2)

def compute_theoretical_and_actual_error(results_repository):
    utilization_data = defaultdict(list)

    for provider_name in ["optimal", "approx"]:
        for trial_idx in range(5):
            trial_name = "sub-trial-%d" % trial_idx
            topo, flows, switches, solutions, net_utilization = read_results(results_repository,
                    provider_name, trial_name)

            most_used_mirroring_port = compute_most_used_mirroring_port(flows, solutions)
            id_to_dpid = topo_mapper.get_and_validate_onos_topo(topo)
            mirror_port_dpid = id_to_dpid[most_used_mirroring_port]
            collector_switch_dpid = topo_mapper.get_collector_switch_dpid()

            utilization = [util_at_time_t[mirror_port_dpid][collector_switch_dpid]
                    for util_at_time_t in net_utilization]
            utilization_data[provider_name].append((len(flows), utilization))

    return utilization_data

def generate_mirroring_port_utilization_bar_plot(results_repository):
    topo, flows, switches, solutions, link_utilization_data = read_results(results_repository, "approx", "sub-trial-4")
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
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), shadow=True, ncol=2)
    plt.rc('text', usetex=True)
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Switch ID")
    plt.ylabel("Mean Mirroring Port Rate ($\\frac{Mb}{s}$)")
    helpers.save_figure("plot-three.pdf")
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
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring port rate ($\\frac{Mb}{s}$)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), shadow=True, ncol=2)

    helpers.save_figure("sfm-theorypractice.pdf")

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
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum mirroring rate ($\\frac{Mb}{s}$)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), shadow=True, ncol=2)

    helpers.save_figure("approx-vs-optimal-theoretical.pdf")

def generate_theoretical_vs_actual_compact_bar_plot(results_repository):
    utilization_data, theoretical_data = compute_theoretical_and_actual_mean_utilization(results_repository)
    actual_error = compute_theoretical_and_actual_error(results_repository)
    std_deviations = defaultdict(list)
    for provider_name, data_list in actual_error.items():
        for flow_count, data in data_list:
            std_deviations[provider_name].append(np.std(
                [util.bytes_per_second_to_mbps(d_i) for d_i in data]))

    width           = 0.35
    ind             = np.arange(5)
    fig, ax         = plt.subplots()
    labels          = ["optimal", "approx"]
    half            = len(labels)//2
    legend_labels   = ["Optimal", "BiSec"]
    colors          = cfg.BAR_PLOT_COLORS
    hatch           = [".", "\\"]
    bar_locations   = [w for w in np.arange((width/2), len(labels)*width, width)]

    pp.pprint(utilization_data)
    pp.pprint(theoretical_data)
    for bar_idx, solution_name in enumerate(labels):
        data_tuples = sorted([(k, v) for k, v in utilization_data[solution_name]],
                key=lambda kvp: kvp[0])
        theoretical_tuples = sorted([(k, v) for k, v in theoretical_data[solution_name]],
                key=lambda kvp: kvp[0])

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
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Number of Flows")
    plt.ylabel("Maximum switch load (Mbps)")
    plt.xticks(ind+(width*len(labels))/2, (ind+1)*10)
    plt.grid()
    plt.xlim(0, max(ind) + (width*len(labels)))
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, cfg.LEGEND_HEIGHT), 
            shadow=True, ncol=len(labels))

    helpers.save_figure("sfm-theorypractice.pdf")

def generate_mirroring_port_utilization_compact_bar_plot(results_repository):
    width               = 0.25
    ind                 = np.arange(11)
    fig, ax             = plt.subplots()
    solution_labels     = SOLUTION_LABELS
    colors              = cfg.BAR_PLOT_COLORS
    hatch               = cfg.BAR_PLOT_TEXTURES
    bar_locations       = [w for w in np.arange((width/2), len(solution_labels)*width, width)]

    # mean_utils :: solution_type -> switch_id -> util_list
    trial_name = "sub-trial-4"
    mean_utils = defaultdict(lambda: defaultdict(list))
    for run_name in ["run-%d" % run_idx for run_idx in range(3)]:
        for solution_name in solution_labels:
            topo, flows, switches, solutions, link_utilization_data = read_results(
                    results_repository, run_name, solution_name, trial_name)
            link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
            collector_switch_dpid   = topo_mapper.get_collector_switch_dpid()
            id_to_dpid              = topo_mapper.get_and_validate_onos_topo(topo)
            dpid_to_id              = {v: k for k, v in id_to_dpid.items()}
            for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
                link_utils_over_time = []
                for time_idx, net_snapshot in enumerate(link_utilization_data):
                    try:
                        link_utils_over_time.append(net_snapshot[s][d])
                    except KeyError:
                        print("net_snapshot at time %d did not contain link %s -> %s" % 
                                (time_idx, s, d))

                source_switch_id = dpid_to_id[s]
                mean_utils[solution_name][source_switch_id].append(
                        util.bytes_per_second_to_mbps(mean(link_utils_over_time[1:])))
    
    for bar_idx, solution_name_to_switch_id in enumerate(mean_utils.items()):
        solution_name, switch_id_to_util_list = solution_name_to_switch_id
        data_tuples = sorted([(switch_id, mean(util_list))
            for switch_id, util_list in switch_id_to_util_list.items()],
            key=lambda kvp: kvp[0])
        std_dev_tuples = sorted([(switch_id, np.std(util_list))
            for switch_id, util_list in switch_id_to_util_list.items()],
            key=lambda kvp: kvp[0])

        ys = [d_i[1] for d_i in data_tuples]
        y_err = [s_i[1] for s_i in std_dev_tuples]

        ax.bar(ind+bar_locations[bar_idx], ys, width, color=colors[bar_idx], hatch=hatch[bar_idx],
                label=solution_labels[solution_name], align="center",
                ecolor="black", yerr=y_err)


    plt.rc('text', usetex=True)
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Switch ID", **cfg.AXIS_LABELS)
    plt.ylabel("Switch load (Mbps)", **cfg.AXIS_LABELS)
    plt.xticks(ind+(width*len(solution_labels))/2, (ind+1))
    plt.grid()
    plt.xlim(0, max(ind) + (width*len(solution_labels)))
    # plt.legend(ncol=len(solution_labels), **cfg.LEGEND)

    helpers.save_figure("sfm-plotthree.pdf", len(solution_labels))

def generate_mirroring_port_utilization_box_plot(results_repository):
    width               = 0.25
    ind                 = np.arange(11)
    fig, ax             = plt.subplots()
    solution_labels     = SOLUTION_LABELS
    colors              = cfg.BAR_PLOT_COLORS
    hatch               = cfg.BAR_PLOT_TEXTURES
    bar_locations       = [w for w in np.arange((width/2), len(solution_labels)*width, width)]

    # mean_util_lists :: solution_type -> switch_id -> util_list
    trial_name = "sub-trial-4"
    mean_util_lists = defaultdict(lambda: defaultdict(list))
    for run_name in ["run-%d" % run_idx for run_idx in range(3)]:
        for solution_name in solution_labels:
            topo, flows, switches, solutions, link_utilization_data = read_results(
                    results_repository, run_name, solution_name, trial_name)
            link_ids = [(s, d) for s, t in link_utilization_data[0].items() for d in t.keys()]
            collector_switch_dpid   = topo_mapper.get_collector_switch_dpid()
            id_to_dpid              = topo_mapper.get_and_validate_onos_topo(topo)
            dpid_to_id              = {v: k for k, v in id_to_dpid.items()}
            for s, d in [(s, d) for s, d in link_ids if d == collector_switch_dpid]:
                link_utils_over_time = []
                for time_idx, net_snapshot in enumerate(link_utilization_data):
                    try:
                        link_utils_over_time.append(net_snapshot[s][d])
                    except KeyError:
                        print("net_snapshot at time %d did not contain link %s -> %s" % 
                                (time_idx, s, d))

                source_switch_id = dpid_to_id[s]
                most_used_id = compute_most_used_mirroring_port(flows, solutions)
                mean_link_utilization_for_run = util.bytes_per_second_to_mbps(mean(
                    link_utils_over_time[1:]))
                if source_switch_id == most_used_id:
                    print(solution_name, mean_link_utilization_for_run)
                mean_util_lists[solution_name][source_switch_id].append(
                        mean_link_utilization_for_run)

    pp.pprint(mean_util_lists) 
    mean_utils = defaultdict(dict)
    box_plot_lists = {}
    for solution_type, switch_id_to_util_list in mean_util_lists.items():
        list_for_solution_type = []
        for switch_id, util_list in switch_id_to_util_list.items():
            # pp.pprint(util_list)
            mean_value = mean(util_list)
            list_for_solution_type.append(mean_value)
            mean_utils[solution_type][switch_id] = mean_value
        box_plot_lists[solution_type] = list_for_solution_type

    box = plt.boxplot([box_plot_lists[solution_name] for solution_name in SOLUTION_NAMES],
            labels=[solution_labels[solution_name] for solution_name in SOLUTION_NAMES],
            patch_artist=True,
            widths=[0.5]*len(SOLUTION_NAMES))
    for element in ["boxes", "whiskers", "fliers", "means", "medians", "caps"]:
        plt.setp(box[element], color="black")

    for idx, patch in enumerate(box["boxes"]):
        patch.set(facecolor=cfg.BAR_PLOT_COLORS[idx], hatch=cfg.BAR_PLOT_TEXTURES[idx])

    plt.rc('text', usetex=True)
    plt.rc('font', **cfg.FONT)
    plt.xlabel("Algorithm", **cfg.AXIS_LABELS)
    plt.ylabel("Switch load (Mbps)", **cfg.AXIS_LABELS)
    plt.grid(**cfg.GRID)

    helpers.save_figure("sfm-boxplot.pdf")
     























