
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot                as plt
import itertools                        as itertools
import numpy                            as np
import pprint                           as pp

import data_visualization.params        as cfg
import data_visualization.helpers       as helpers

from collections                        import defaultdict

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

def generate_data_recovery_vs_param_plot(trial_provider, param_name, x_axis_label):
    param_selector = lambda t_i: t_i.get_parameter(param_name)
    sorted_trials = sorted(trial_provider, key=param_selector)
    xs = []
    attacker_types = [ "random-path-hopping"
                     , "random-node-hopping"
                     # , "ideal-random-path-hopping"
                     , "one-node-per-path"
                     , "fixed"
                     , "planned"
                     ]
    means = defaultdict(list)
    errs = defaultdict(list)
    attacker_data = {}
    fig, ax = plt.subplots()
    for param_value, param_group in itertools.groupby(sorted_trials, key=param_selector):
        param_group = list(param_group)
        ys = defaultdict(list)
        for trial in param_group:
            total_messages_sent = trial.get_parameter("sim-duration")
            for attacker_type in attacker_types:
                attacker_data[attacker_type] = trial.get_parameter(
                        f"{attacker_type}-attacker-recovered-messages")
            for attacker_type, recovered_messages in attacker_data.items():
                print(f"{attacker_type} recoverd {len(recovered_messages)} out of {total_messages_sent} messages")
                ys[attacker_type].append((len(recovered_messages) / total_messages_sent) * 100)

        xs.append(param_value)
        for attacker_type, y_vals in ys.items():
            means[attacker_type].append(np.mean(y_vals))
            errs[attacker_type].append(np.std(y_vals))

    for plot_idx, (attacker_type, means) in enumerate(means.items()):
        helpers.plot_a_scatter(xs, means, idx=plot_idx, axis_to_plot_on=ax, label=attacker_type)

    # axins = ax.inset_axes([0.5, 0.6, 0.47, 0.37])
    # axins.set_xscale("log")
    # ax.set_xscale("log")
    # x1, x2, y1, y2 = 0, 100, -10, 500
    # axins.set_xlim(x1, x2)
    # axins.set_ylim(y1, y2)
    # axins.set_xticklabels("")
    # axins.set_yticklabels("")

    # helpers.plot_a_scatter(xs, random_path_means, idx=0, label="Random Path Attacker",
    #         axis_to_plot_on=axins)
    # helpers.plot_a_scatter(xs, random_node_means, idx=1, label="Random Node Attacker",
    #         axis_to_plot_on=axins)
    # helpers.plot_a_scatter(xs, one_node_per_path_means, idx=2, label="One Node per Path Attacker",
    #         axis_to_plot_on=axins)
    # helpers.plot_a_scatter(xs, fixed_means, idx=3, label="Fixed Attacker",
    #         axis_to_plot_on=axins)
    # ax.indicate_inset_zoom(axins, label=None)

    helpers.xlabel(x_axis_label)
    helpers.ylabel(r"\% of recovered messages")
    helpers.save_figure("attacker-simulation.pdf", num_cols=3)

def generate_data_recovery_vs_time_cdf(trial_provider):
    for trial in trial_provider:
        if trial.get_parameter("path-length") == 10:
            random_path_attacker = trial.get_parameter(
                    "random-path-hopping-attacker-recovered-messages")
            random_node_attacker = trial.get_parameter(
                    "random-node-hopping-attacker-recovered-messages")
            ideal_path_attacker  = trial.get_parameter(
                    "ideal-random-path-hopping-attacker-recovered-messages")
            one_node_per_path_attacker_captured = trial.get_parameter("one-node-per-path-attacker")
            fixed_attacker_captured = trial.get_parameter("fixed-attacker")
            
            helpers.plot_a_cdf(sorted(random_path_attacker), idx=0, label="Random Path Attacker",
                    plot_markers=False)
            helpers.plot_a_cdf(sorted(random_node_attacker), idx=1, label="Random Node Attacker",
                    plot_markers=False)
            helpers.plot_a_cdf(sorted(one_node_per_path_attacker_captured), idx=2,
                    label="One Node per Path Attacker", plot_markers=False)
            helpers.plot_a_cdf(sorted(fixed_attacker_captured), idx=3, label="Fixed Attacker",
                    plot_markers=False)

    helpers.save_figure("data-recovery-cdf.pdf", num_cols=2)



















