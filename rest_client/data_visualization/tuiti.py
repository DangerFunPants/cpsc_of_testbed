import matplotlib
matplotlib.use("Agg")

import pathlib                      as path
import pprint                       as pp
import itertools                    as itertools
from operator                       import itemgetter
from collections                    import defaultdict

import matplotlib.pyplot            as plt
import numpy                        as np

import data_visualization.helpers               as helpers
import data_visualization.params                as cfg
from data_visualization.helpers     import marker_style, line_style, line_color
from nw_control.stat_monitor        import OnMonitor

plt.rc("text", usetex=True)
plt.rc("font", **cfg.FONT)
matplotlib.rcParams['text.latex.preamble']  = [ r"\usepackage{amsmath}"
                                              , r"\usepackage{amssymb}"
                                              , r"\usepackage{amsfonts}"
                                              , r"\usepackage{amsthm}"
                                              , r"\usepackage{graphics}"
                                              ]
matplotlib.rcParams["xtick.direction"]      = "in"
matplotlib.rcParams["ytick.direction"]      = "in"

def link_tuple_to_util_list(link_utilization_over_time):
    data_for_links = defaultdict(list)
    for link_id_to_util_value in link_utilization_over_time:
        for link_tuple, util_value in link_id_to_util_value.items():
            data_for_links[link_tuple].append(util_value)

    return {key: value for key, value in data_for_links.items()}

def get_link_set(util_results):
    link_set = set()
    for results_list in util_results:
        for results_set in results_list:
            link_set.add((results_set["sourceSwitchId"], results_set["destinationSwitchId"]))
            link_set.add((results_set["destinationSwitchId"], results_set["sourceSwitchId"]))
    return link_set

def generate_link_utilization_cdf(trial_provider):
    """
    Generate a CDF that shows the mean utilization of each link for every trial in the
    provider.
    """
    link_capacity = 50.0 # Mi-bps
    for idx, trial in enumerate(trial_provider):
        utilization_results = trial.get_parameter("byte-counts-over-time")
        links = get_link_set(utilization_results)
        print(f"Number of links based on utilization results: {len(links)}")

        mean_network_utilization = trial.get_parameter("measured-link-utilization")
        link_utilizations = sorted([link_throughput / link_capacity 
                for link_throughput 
                in mean_network_utilization.values()])
        helpers.plot_a_cdf(link_utilizations, label=trial.name, idx=idx)

    plt.xlabel("Link Utilization")
    plt.ylabel(r"$\mathbb{P}\{x < \mathcal{X}$\}")
    plt.legend(ncol=len(trial_provider), **cfg.LEGEND)
    helpers.save_figure("cdf.pdf", no_legend=True)

def generate_link_utilization_box_plot(trial_provider):
    """
    Generate a box and whisker blot that shows the mean utilization of every link for every
    trial in the provider.
    """
    def plot_a_box_plot(data_vectors, vector_labels):
        bp = plt.boxplot(data_vectors, labels=vector_labels,
                whiskerprops={"linestyle": "--"},
                flierprops={"marker": "x", "markerfacecolor": "red", "markeredgecolor": "red"})
        plt.setp(bp["boxes"], color="blue")
        plt.setp(bp["medians"], color="red")

    box_plot_data = []
    labels = []
    for the_trial in trial_provider:
        labels.append(the_trial.name)
        mean_link_utilization = the_trial.get_parameter("measured-link-utilization")
        box_plot_data.append(list(mean_link_utilization.values()))

    plot_a_box_plot(box_plot_data, labels)
    helpers.save_figure("box-plot.pdf")

def generate_link_utilization_over_time_plot(trial_provider):
    """
    Generate a plot of link utilization over time for a single trial
    """
    data_to_plot = []
    xs = []
    for the_trial in [t for t in trial_provider if t.name == "avg"]:
        print(f"Graphing trial with name: {the_trial.name}")
        link_utilization_over_time = the_trial.get_parameter("link-utilization-over-time")
        data_for_links = {link_tuple: util_list 
                            for link_tuple, util_list 
                            in link_tuple_to_util_list(link_utilization_over_time) 
                            if link_tuple[0] == "of:0000000000000001"}

        for plot_idx, (link_tuple, utilization_values) in enumerate(data_for_links.items()):
            xs = [i for i in range(len(utilization_values))]
            ys = utilization_values
            helpers.plot_a_scatter(xs, ys, idx=plot_idx)

        helpers.save_figure("over-time.pdf", no_legend=True)

def generate_per_path_packet_loss_cdf(trial_provider):
    """
    For each trial generate a cdf of total packet loss 
    ((i.e. total packets sent - total packets received) / total packets sent)
    """
    for trial_idx, the_trial in enumerate(trial_provider):
        end_host_results = the_trial.get_parameter("end-host-results")
        sender_results = end_host_results[0]["sender"]
        # print("Sender results:\n")
        # pp.pprint(sender_results)

        receiver_results = end_host_results[1]["receiver"]
        # print("Receiver results:\n")
        # pp.pprint(receiver_results)

        link_loss_rates = []
        flow_id_selector = lambda ss: ss["flow_id"]
        sender_results = sorted(list(sender_results.values()), key=flow_id_selector)
        for flow_id, flows_with_id in itertools.groupby(sender_results, flow_id_selector):
            total_sender_packets_for_path = 0
            total_receiver_packets_for_path = 0
            for the_flow in flows_with_id:
                source_port = the_flow["src_port"]
                total_sender_packets_for_path += the_flow["pkt_count"]
                total_receiver_packets_for_path += sum([packet_count 
                        for receiver_info, packet_count
                        in receiver_results.items()
                        if receiver_info[1] == source_port])
            link_loss_rate = (total_sender_packets_for_path - total_receiver_packets_for_path) \
                    / total_sender_packets_for_path
            link_loss_rates.append(link_loss_rate)

        helpers.plot_a_cdf(sorted(link_loss_rates), idx=trial_idx, label=the_trial.name)

    plt.xlabel(helpers.axis_label_font("Packet Loss Rate"))
    plt.ylabel(helpers.axis_label_font(r"$\mathbb{P}\{x \leq \mathcal{X}\}$"))
    helpers.save_figure("per-path-loss-cdf.pdf")

def generate_mean_throughput_over_time_plot(trial_provider):
    """
    Generate a graph that shows the mean throughput across all the links over time for 
    each trial in trial provider.
    """
    path_capacity = 50.0
    for trial_idx, the_trial in enumerate(trial_provider):
        # number_of_paths = the_trial.get_parameter("number-of-paths")
        link_utilization_over_time = the_trial.get_parameter("link-utilization-over-time")
        data_for_links = {link_tuple: util_list
                for link_tuple, util_list 
                in link_tuple_to_util_list(link_utilization_over_time).items()
                if link_tuple[0] == "of:0000000000000001"}
        ys = {link_tuple: [min(path_capacity, util_val) for util_val in util_val_list]
                for link_tuple, util_val_list in data_for_links.items()}
        throughputs_over_time = []
        for time_idx in range(len(next(iter(data_for_links.values())))):
            total_throughput = sum(util_list[time_idx] for util_list in ys.values())
            throughputs_over_time.append(total_throughput)
        xs = [idx for idx in range(len(next(iter(data_for_links.values()))))]
        helpers.plot_a_scatter(xs, throughputs_over_time, idx=trial_idx, label=the_trial.name)

    plt.xlabel(helpers.axis_label_font("Time"))
    plt.ylabel(helpers.axis_label_font("Mean throughput (Mi-bps)"))
    helpers.save_figure("throughput-over-time.pdf", num_cols=len(trial_provider))

def generate_mean_link_utilization_over_time_plot(trial_provider):
    """
    Generate a graph that shows the mean utilization across all the links over time
    for each trial in the trial provider
    """
    path_capacity = 50.0
    for trial_idx, the_trial in enumerate(trial_provider):
        link_utilization_over_time = the_trial.get_parameter("link-utilization-over-time")
        data_for_links = {link_tuple: util_list
                for link_tuple, util_list
                in link_tuple_to_util_list(link_utilization_over_time).items()
                if link_tuple[0] == "of:0000000000000001"}
        ys = {link_tuple: [min(path_capacity, util_val) / path_capacity for util_val in util_val_list]
                for link_tuple, util_val_list in data_for_links.items()}
        # The next line assumes that the same number of network snapshots were captured
        # for each of the links, I think this will always happen but this will throw
        # if that is not the case.
        throughputs_over_time = [np.mean([util_list[time_idx] for util_list in ys.values()])
                for time_idx in range(len(next(iter(data_for_links.values()))))]
        xs = [idx for idx in range(len(next(iter(data_for_links.values()))))]
        helpers.plot_a_scatter(xs, throughputs_over_time, idx=trial_idx, label=the_trial.name)


    plt.xlabel(helpers.axis_label_font("Time"))
    plt.ylabel(helpers.axis_label_font("Mean link utilization"))
    helpers.save_figure("mean-utilization-over-time.pdf", num_cols=len(trial_provider))

