
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot                as plt
import itertools                        as itertools
import numpy                            as np

import data_visualization.params        as cfg
import data_visualization.helpers       as helpers

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

    random_path_means = []
    random_node_means = []
    ideal_path_means = []

    random_path_err = []
    random_node_err = []
    ideal_path_err = []

    fig, ax = plt.subplots()

    for param_value, param_group in itertools.groupby(sorted_trials, key=param_selector):
        param_group = list(param_group)

        random_path_ys = []
        random_node_ys = []
        ideal_path_ys = []
        for trial in param_group:
            random_path_attacker = trial.get_parameter(
                    "random-path-hopping-attacker-recovered-messages")
            random_node_attacker = trial.get_parameter(
                    "random-node-hopping-attacker-recovered-messages")
            ideal_path_attacker  = trial.get_parameter(
                    "ideal-random-path-hopping-attacker-recovered-messages")

            random_path_captured = random_path_attacker
            random_node_captured = random_node_attacker
            ideal_path_captured = ideal_path_attacker

            random_path_ys.append(len(random_path_captured))
            random_node_ys.append(len(random_node_captured))
            ideal_path_ys.append(len(ideal_path_captured))

        xs.append(param_value)
        random_path_means.append(np.mean(random_path_ys))
        random_node_means.append(np.mean(random_node_ys))
        ideal_path_means.append(np.mean(ideal_path_ys))

        random_path_err.append(np.std(random_path_ys))
        random_node_err.append(np.std(random_node_ys))
        ideal_path_err.append(np.std(ideal_path_ys))

    helpers.plot_a_scatter(xs, random_path_means, idx=0, label="Random Path Attacker",
            axis_to_plot_on=ax)
    helpers.plot_a_scatter(xs, random_node_means, idx=1, label="Random Node Attacker",
            axis_to_plot_on=ax)
    helpers.plot_a_scatter(xs, ideal_path_means, idx=2, label="Ideal Path Attacker",
            axis_to_plot_on=ax)

    axins = ax.inset_axes([0.5, 0.6, 0.47, 0.37])
    x1, x2, y1, y2 = 0, 100, 0, 1000
    axins.set_xlim(x1, x2)
    axins.set_ylim(y1, y2)
    axins.set_xticklabels("")
    axins.set_yticklabels("")

    helpers.plot_a_scatter(xs, random_path_means, idx=0, label="Random Path Attacker",
            axis_to_plot_on=axins)
    helpers.plot_a_scatter(xs, random_node_means, idx=1, label="Random Node Attacker",
            axis_to_plot_on=axins)
    ax.indicate_inset_zoom(axins, label=None)

    helpers.xlabel(x_axis_label)
    helpers.ylabel(r"\# of recovered messages.")
    helpers.save_figure("attacker-simulation.pdf", num_cols=3)

