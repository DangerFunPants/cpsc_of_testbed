
import matplotlib 
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import numpy                        as np
import pprint                       as pp
import pathlib                      as path
import itertools                    as itertools
import operator                     as operator

import data_visualization.params    as cfg
import data_visualization.helpers   as helpers

from collections import defaultdict


plt.rc("text", usetex=True)
plt.rc("font", **cfg.FONT)
matplotlib.rcParams["xtick.direction"]      = "in"
matplotlib.rcParams["ytick.direction"]      = "in"
matplotlib.rcParams["text.latex.preamble"]  = [ r"\usepackage{amsmath}"
                                              , r"\usepackage{amssymb}"
                                              , r"\usepackage{amsfonts}"
                                              , r"\usepackage{amsthm}"
                                              , r"\usepackage{graphics}"
                                              ]

MININET_RESULTS_DIR = path.Path("/home/cpsc-net-user/repos/mtd-crypto-impl/results/")

def compute_parameter_statistics(trial_dicts, selector_fn, aggregation_fn):
    trial_dicts = sorted(trial_dicts, key=selector_fn)
    scatter_points = []
    for key_value, g in itertools.groupby(trial_dicts, selector_fn):
        measured_statistic = []
        for d_i in g:
            try:
                statistic_value = aggregation_fn(d_i)
            except ValueError as ex:
                print("Failed to compute statistic value: %s" % ex)
                continue

            measured_statistic.append(statistic_value)
        scatter_points.append((key_value, np.mean(statistic_value),
            np.std(statistic_value)))
    return scatter_points

def compute_mean_goodput(trial_dicts, selector_fn):
    def compute_goodput(trial_dict):
        elapsed_time_us = trial_dict["receiver_last_recv_time"] - \
                trial_dict["receiver_first_recv_time"]
        elapsed_time_s = elapsed_time_us / 10**6
        data_volume_bits = 10 * 10**6 * 8
        if elapsed_time_s == 0:
            raise ValueError("Elapsed time was zero.")
        goodput_bps = data_volume_bits / elapsed_time_s
        return goodput_bps / 10**6
    return compute_parameter_statistics(trial_dicts, selector_fn, compute_goodput)

def compute_mean_data_recovery(trial_dicts, selector_fn):
    # trial_dicts = sorted(trial_dicts, key=selector_fn)
    # scatter_points = []
    # pp.pprint(trial_dicts)
    # for key_value, g in itertools.groupby(trial_dicts, selector_fn):
    #     measured_data_recovery = []
    #     for d_i in g:
    #         measured_data_recovery.append(d_i["attacker_intercepted_bytes"])

    #     print("Number of trials: %d" % len(measured_data_recovery))
    #     scatter_points.append((key_value, np.mean(measured_data_recovery),
    #         np.std(measured_data_recovery)))

    # return scatter_points
    def compute_data_recovery(trial_dict):
        return trial_dict["attacker_intercepted_bytes"]
    return compute_parameter_statistics(trial_dicts, selector_fn, compute_data_recovery)

def generate_goodput_vs_k_scatter():
    results_file = MININET_RESULTS_DIR / "results_k" / "results.log"
    results_dicts = [eval(s_i) for s_i in results_file.read_text().splitlines()]

    host_hopping_trials = [d_i for d_i in results_dicts 
            if d_i["experiment"]["hop_method"] == "host"]
    net_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "net"]

    k_selector = lambda d_i: d_i["experiment"]["k"]
    # Plot the host hopping results
    scatter_points = compute_mean_goodput(host_hopping_trials, k_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=0, label=helpers.legend_font("Host hopping"))

    # Plot the net hopping results
    scatter_points = compute_mean_goodput(net_hopping_trials, k_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=1, label=helpers.legend_font("Net hopping"))
    

    plt.xlabel(helpers.axis_label_font(r"$K$"))
    plt.ylabel(helpers.axis_label_font("Mbps"))
    helpers.save_figure("k_goodput.pdf", num_cols=2)

def generate_goodput_vs_path_length_scatter():
    results_file = MININET_RESULTS_DIR / "results_links" / "results.log"
    results_dicts = [eval(s_i) for s_i in results_file.read_text().splitlines()]
    
    host_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "host"]
    net_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "net"]

    path_length_selector = lambda d_i: d_i["experiment"]["path_length"]

    scatter_points = compute_mean_goodput(host_hopping_trials, path_length_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=0, label=helpers.legend_font("Host hopping"))

    scatter_points = compute_mean_goodput(net_hopping_trials, path_length_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=1, label=helpers.legend_font("Net hopping"))

    plt.xlabel(helpers.axis_label_font("Path length (\# of links)"))
    plt.ylabel(helpers.axis_label_font("Mbps"))
    helpers.save_figure("links_goodput.pdf", num_cols=2)

def generate_goodput_vs_hopping_interval_scatter():
    results_file = MININET_RESULTS_DIR / "results_ts" / "results.log"
    results_dicts = [eval(s_i) for s_i in results_file.read_text().splitlines()]
    
    host_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "host"]
    net_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "net"]

    hopping_interval_selector = lambda d_i: d_i["experiment"]["timestep"]

    scatter_points = compute_mean_goodput(host_hopping_trials, hopping_interval_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=0, label=helpers.legend_font("Host hopping"))

    scatter_points = compute_mean_goodput(net_hopping_trials, hopping_interval_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=1, label=helpers.legend_font("Net hopping"))

    plt.xlabel(helpers.axis_label_font("Timestep (ms)"))
    plt.ylabel(helpers.axis_label_font("Mbps"))
    helpers.save_figure("ts_goodput.pdf", num_cols=2)

def generate_goodput_vs_message_size_scatter():
    results_file = MININET_RESULTS_DIR / "results_msgsize" / "results.log"
    results_dicts = [eval(s_i) for s_i in results_file.read_text().splitlines()]

    host_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "host"]
    net_hopping_trials = [d_i for d_i in results_dicts
            if d_i["experiment"]["hop_method"] == "net"]

    msg_size_selector = lambda d_i: d_i["experiment"]["msg_size"]

    scatter_points = compute_mean_goodput(host_hopping_trials, msg_size_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=0, label=helpers.legend_font("Host hopping"))

    scatter_points = compute_mean_goodput(net_hopping_trials, msg_size_selector)
    xs = [t_i[0] for t_i in scatter_points]
    ys = [t_i[1] for t_i in scatter_points]
    helpers.plot_a_scatter(xs, ys, idx=1, label=helpers.legend_font("Net hopping"))

    plt.xlabel(helpers.axis_label_font("Message size (Bytes)"))
    plt.ylabel(helpers.axis_label_font("Mbps"))
    helpers.save_figure("msg_goodput.pdf", num_cols=2)

def generate_attacker_vs_k_scatter():
    def attacker_setting(trial_dict):
        return trial_dict["experiment"]["attacker_setting"]
    results_file = MININET_RESULTS_DIR / "results_attacker_k" / "results.log"
    
    results_dicts = [eval(s_i) for s_i in results_file.read_text().splitlines()]
    # pp.pprint([attacker_setting(d_i) for d_i in results_dicts])
    fixed_attacker_trials = [d_i for d_i in results_dicts
            if attacker_setting(d_i) == "fixed"]
    unsynced_attacker_trials = [d_i for d_i in results_dicts
            if attacker_setting(d_i) == "hop_independent"]
    synced_attacker_trials = [d_i for d_i in results_dicts
            if attacker_setting(d_i) == "hop_sync"]

    trial_data_list = [fixed_attacker_trials, unsynced_attacker_trials, synced_attacker_trials]
    trial_names = ["Fixed", "Not synced", "Synced"]
    k_selector = lambda d_i: d_i["experiment"]["k"]
    for plot_idx, (trial_name, trial_data) in enumerate(zip(trial_names, trial_data_list)):
        scatter_points = compute_mean_data_recovery(trial_data, k_selector)
        # pp.pprint(scatter_points)
        xs = [t_i[0] for t_i in scatter_points]
        ys = [t_i[1]/1000 for t_i in scatter_points] # to KB
        helpers.plot_a_scatter(xs, ys, idx=plot_idx, 
                label=helpers.legend_font(trial_name))

    plt.xlabel(helpers.axis_label_font("$K$"))
    plt.ylabel(helpers.axis_label_font("Kilobytes"))
    helpers.save_figure("attacker.pdf", num_cols=len(trial_data_list))

def generate_all_plots():
    generate_goodput_vs_k_scatter()
    generate_goodput_vs_message_size_scatter()
    generate_goodput_vs_path_length_scatter()
    generate_goodput_vs_hopping_interval_scatter()
    generate_attacker_vs_k_scatter()

















