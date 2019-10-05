import matplotlib
matplotlib.use("Agg")

import data_visualization.params        as cfg

import matplotlib.pyplot                as plt
import json                             as json
import numpy                            as np

from collections import defaultdict

def tick_font(tick_label, precision="%.2f"):
    if type(tick_label) == type(np.float64(1.0)):
        s = r"\text{\LARGE{\textsf{%s}}}" % precision
        return s % tick_label
    else:
        return r"\text{\LARGE{\textsf{%s}}}" % tick_label

def axis_label_font(phrase):
    return huge(phrase)

def xlabel(phrase):
    plt.xlabel(axis_label_font(phrase))

def ylabel(phrase):
    plt.ylabel(axis_label_font(phrase))

def legend_font(phrase):
    return huge(phrase)

def LARGE(phrase):
    return r"\LARGE{%s}" % phrase

def huge(phrase):
    return r"\huge{%s}" % phrase

def bf(phrase):
    return r"\textbf{%s}" % phrase

def trial_name_font(phrase):
    return r"\scalebox{0.7}[1.0]{\textsf{%s}}" % phrase

def super_title_font(phrase):
    return r"\normalsize{%s}" % phrase

def sub_title_font(phrase):
    return r"\small{%s}" % phrase

def idx_list_circular(idx, the_list):
    return the_list[idx%len(the_list)]

def marker_style(idx):
    return idx_list_circular(idx, cfg.MARKER_STYLE)

def line_style(idx):
    return idx_list_circular(idx, cfg.LINE_STYLE)

def line_color(idx):
    return idx_list_circular(idx, cfg.LINE_COLOR)

def marker_color(idx):
    return idx_list_circular(idx, cfg.MARKER_COLOR)

def bar_color(idx):
    return idx_list_circular(idx, cfg.BAR_PLOT_COLORS)

def bar_texture(idx):
    return idx_list_circular(idx, cfg.BAR_PLOT_TEXTURES)

def save_figure( figure_name
               , num_cols           = 1
               , legend_kwargs      = cfg.LEGEND
               , **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    kwargs["bbox_inches"] = "tight"
    plt.tick_params(labelsize=15)
    plt.grid(**cfg.GRID)
    if not ("no_legend" in kwargs and kwargs["no_legend"]):
        legend = plt.legend(ncol=num_cols, **legend_kwargs)
    plt.gca().set_axisbelow(True)
    plt.savefig(str(p), **kwargs) 
    plt.clf()

def save_subfigure_plot( figure_name
                       , plot_axis
                       , num_cols   = 1
                       , **kwargs):
    p = cfg.FIGURE_OUTPUT_PATH.joinpath(figure_name)
    kwargs["bbox_inches"] = "tight"
    for ax in plot_axis:
        ax.tick_params(labelsize=15)
        ax.grid(**cfg.GRID)
        ax.set_axisbelow(True)

    if not ("no_legend" in kwargs and kwargs["no_legend"]):
        legend = plt.legend(ncol=num_cols, **cfg.LEGEND)
    
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

def plot_a_cdf( sorted_cdf_data
              , idx             = 0
              , label           = None
              , plot_markers    = True
              , axis_to_plot_on = None
              , label_data      = True):
    print("CDF data length %d" % len(sorted_cdf_data))
    if label == None:
        label = "CDF %d" % idx
    xs = [0.0]
    ys = [0.0]
    for ctr, d_i in enumerate(sorted_cdf_data):
        xs.append(d_i)
        ys.append(ctr / len(sorted_cdf_data))

    if axis_to_plot_on == None:
        axis_to_plot_on = plt

    plot_kwargs = { "linestyle"     : line_style(idx)
                  , "color"         : line_color(idx)
                  }

    if plot_markers:
        plot_kwargs["marker"] = marker_style(idx)

    if label_data:
        plot_kwargs["label"] = label

    axis_to_plot_on.plot(xs, ys, **plot_kwargs)

def plot_a_bar( bar_x_locations
              , bar_y_values
              , idx                 = 0
              , label               = None
              , axis_to_plot_on     = None
              , label_data          = True
              , bar_width           = 0.5):
    if label == None:
        label = "BAR %d" % idx
    
    if axis_to_plot_on == None:
        axis_to_plot_on = plt

    plot_kwargs = { "color"     : bar_color(idx)
                  , "hatch"     : bar_texture(idx)
                  , "width"     : bar_width
                  }

    if label_data:
        plot_kwargs["label"] = label

    axis_to_plot_on.bar(bar_x_locations, bar_y_values, **plot_kwargs)
    
    # Workaround since hatching does not appear to be working in this version of
    # matplotlib
    plot_kwargs["label"] = None
    plot_kwargs["color"] = "None"
    axis_to_plot_on.bar(bar_x_locations, bar_y_values, **plot_kwargs)

def plot_a_scatter( xs
                  , ys
                  , idx             = 0
                  , label_data      = True
                  , plot_markers    = True
                  , err             = None
                  , label           = None
                  , axis_to_plot_on = None):
    if label == None:
        label = "SCATTER %d" % idx

    if axis_to_plot_on == None:
        axis_to_plot_on = plt

    plot_kwargs = { "linestyle"     : line_style(idx)
                  , "color"         : line_color(idx)
                  }
    
    if plot_markers:
        plot_kwargs["marker"] = marker_style(idx)

    if label_data:
        plot_kwargs["label"] = label

    if err != None:
        # plot_kwargs["err"] = err
        # axis_to_plot_on.errorbar(xs, ys, yerr=err, **plot_kwargs)
        pass

    axis_to_plot_on.plot(xs, ys, **plot_kwargs)






