
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import networkx                     as nx
import numpy                        as np
import json                         as json
import pprint                       as pp
import pathlib                      as path
import itertools                    as itertools
import scipy                        as scipy
import scipy.stats 

import data_visualization.params        as cfg
import data_visualization.helpers       as helpers
import simulations.simulation_trial     as simulation_trial

from collections                    import defaultdict
from statistics                     import mean

FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

def read_results(results_repository, flow_count, node_count, seed_number):
    schema_vars = { "node-count"    : str(node_count)
                  , "flow-count"    : str(flow_count)
                  , "seed-number"   : str(seed_number)
                  }
    files = ["sim-results.json"]
    results = results_repository.read_trial_results(schema_vars, files)

    return simulation_trial.SimulationTrial.from_json(results["sim-results.json"])

def generate_simulation_run_time_plot(results_repository):
    def mean_confidence_interval(data, confidence=0.95):
        a = 1.0 * np.array(data)
        n = len(a)
        m, se = np.mean(a), scipy.stats.sem(a)
        h = se * scipy.stats.t.ppf((1 + confidence) / 2., n-1)
        # return m, m-h, m+h
        return h

    series_data = {}

    for flow_count in [100, 500, 1000]:
        data_for_node_counts = []
        for node_count in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
            data_for_single_count = []
            seed_numbers = [ 742349042
                           , 2787879137
                           , 3102739139
                           , 2303690384
                           , 1672982999
                           , 2501915964
                           , 2853959085
                           , 3163893110
                           , 462786850
                           , 4124106680
                           ]

            for seed_number in seed_numbers:
                sim = read_results(results_repository, flow_count, node_count, seed_number)
                data_for_single_count.append(sim.solution_time)
            pp.pprint(data_for_single_count)
            ci = mean_confidence_interval(data_for_single_count)
            data_for_node_counts.append((node_count, np.mean(data_for_single_count), 
                ci))
        series_data[flow_count] = data_for_node_counts
    
    for idx, (flow_count, data_for_node_counts) in enumerate(sorted(series_data.items(), 
        key=lambda t: t[0])):
        xs          = [d_i[0] for d_i in data_for_node_counts]
        ys          = [d_i[1] for d_i in data_for_node_counts]
        std_dev     = [d_i[2] for d_i in data_for_node_counts]
        plt.errorbar(xs, ys, label="\\LARGE{%d VLs}" % flow_count, marker=cfg.MARKER_STYLE[idx],
                linestyle=helpers.line_style(idx), color=helpers.line_color(idx),
                yerr=std_dev, capsize=2)

    plt.rc("text", usetex=True)
    matplotlib.rcParams['text.latex.preamble'] = [r'\usepackage{amsmath}', r'\usepackage{amssymb}']
    plt.rc("font", **cfg.FONT)
    plt.rc("legend", edgecolor="black")
    xtick_locations = [200, 400, 600, 800, 1000]
    ytick_locations = [2, 4, 6, 8, 10, 12, 14]
    plt.xticks(xtick_locations, [helpers.tick_font(x_i) for x_i in xtick_locations])
    plt.yticks(ytick_locations, [helpers.tick_font(y_i) for y_i in ytick_locations])
    plt.xlabel("Number of Nodes", **cfg.AXIS_LABELS)
    plt.ylabel("Running Time (s)", **cfg.AXIS_LABELS)
    helpers.save_figure("sim-running-time.pdf", 1)
