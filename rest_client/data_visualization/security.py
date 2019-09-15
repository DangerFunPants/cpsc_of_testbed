
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot                        as plt
import pathlib                                  as path
import pprint                                   as pp
import itertools                                as itertools
import numpy                                    as np

import data_visualization.params                as cfg
import data_visualization.helpers               as helpers

from collections                    import namedtuple, defaultdict, Counter

from data_visualization.helpers     import marker_style, line_style, line_color

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

PacketInfo = namedtuple("PacketInfo", 
        "source_ip destination_ip source_port destination_port seq_num share_num timestamp")

def read_literal_from_file(file_path):
    with file_path.open("r") as fd:
        file_bytes = fd.read()
    return eval(file_bytes)

def read_packet_dump_info_from_file(file_path):
    list_literal = read_literal_from_file(file_path)
    packet_infos = [PacketInfo(*t_i) for t_i in list_literal]
    return packet_infos

def plot_share_delay_histogram(packets):
    """
    Takes a list of PacketInfo tuples as input and plots the PDF of the intershare delay.
    """
    seq_num_to_ts = defaultdict(list)
    for p_i in packets:
        seq_num_to_ts[p_i.seq_num].append(p_i.timestamp)

    inter_share_delays = []
    for seq_num, ts in seq_num_to_ts.items():
        inter_share_delay = max(ts) - min(ts)
        inter_share_delays.append(inter_share_delay)
    
    plt.histogram(inter_share_delays, density=True)
    helpers.save_figure("share-delay-pdf.pdf")

def plot_share_delay_cdf(packets, **kwargs):
    """
    Generate a plot of the cumulative distribution function of the inter-share delay for 
    a path hopping transfer.
    """
    seq_num_to_ts = defaultdict(list)
    for p_i in packets:
        seq_num_to_ts[p_i.seq_num].append(p_i.timestamp)

    inter_share_delays = []
    for seq_num, ts in seq_num_to_ts.items():
        inter_share_delay = max(ts) - min(ts)
        inter_share_delays.append(inter_share_delay)

    inter_share_delays_ms = sorted([isd/1000 for isd in inter_share_delays])
    helpers.plot_a_cdf(inter_share_delays_ms, plot_markers=False, **kwargs)

def plot_best_and_worst_paths_cdf(packets, **kwargs):
    """
    Generate a plot showing the cumulative distribution function of the inter-share delay
    for the 5 best and 5 worst K-sized sets of paths in the network. In this context
    The terms best and worst refer to the K-sized sets of paths with the smallest and 
    largest inter-share delay respectively.
    """
    def configure_plot(figure):
        pass

    # want to group by the sequence number and the set of ports
    key_fn = lambda p_i: p_i.seq_num
    packets = sorted(packets, key=key_fn)
    groups = itertools.groupby(packets, key_fn)
    port_group_to_isd = defaultdict(list)
    for seq_num, packets_with_seq_num in groups:
        packet_group = list(packets_with_seq_num)
        port_key = tuple(sorted([p_i.destination_port for p_i in packet_group]))
        ts_selector = lambda p_i: p_i.timestamp
        inter_share_delay = ts_selector(max(packet_group, key=ts_selector)) - \
                ts_selector(min(packet_group, key=ts_selector))
        port_group_to_isd[port_key].append(inter_share_delay / 1000)
    
    def compute_95th_percentile(data):
        data = sorted(data)
        idx = int(np.floor(0.95 * len(data)))
        return data[idx]

    fig, axs = plt.subplots(2, sharex=True)
    best_paths_axis = axs[0]
    worst_paths_axis = axs[1]
    best_paths_axis.set_title(helpers.sub_title_font("Best paths"))
    worst_paths_axis.set_title(helpers.sub_title_font("Worst paths"))
    sorted_paths = sorted([(port_key, inter_share_delays) 
            for port_key, inter_share_delays in port_group_to_isd.items()],
            key=lambda t_i: np.mean(t_i[1]))
    best_paths = sorted_paths[:5]
    worst_paths = sorted_paths[len(sorted_paths)-5:]
    for plot_idx, (port_group, inter_share_delays) in enumerate(best_paths):
        helpers.plot_a_cdf(sorted(inter_share_delays), idx=plot_idx, plot_markers=False,
                axis_to_plot_on=best_paths_axis, label_data=False)

    all_latencies = list(itertools.chain(*[b_i[1] for b_i in best_paths]))
    percentile_95 = compute_95th_percentile(all_latencies)
    best_paths_axis.axvline(percentile_95, color="red", linestyle="--", label="$95$th-Percentile")
    best_paths_axis.legend(ncol=1, **cfg.LEGEND)

    for plot_idx, (port_group, inter_share_delays) in enumerate(worst_paths):
        helpers.plot_a_cdf(sorted(inter_share_delays), idx=plot_idx, plot_markers=False,
                axis_to_plot_on=worst_paths_axis, label_data=False)
    
    all_latencies = list(itertools.chain(*[w_i[1] for w_i in worst_paths]))
    percentile_95 = compute_95th_percentile(all_latencies)
    worst_paths_axis.axvline(percentile_95, color="red", linestyle="--", label="$95$th-Percentile")

    y_label_str = r"$\mathbb{P}\{x < \mathcal{X}\}$"
    worst_paths_axis.set_xlabel(r"Inter-Share Delay ($ms$)")
    worst_paths_axis.set_ylabel(y_label_str)
    best_paths_axis.set_ylabel(y_label_str)

    configure_plot(fig)
    axis_to_plot = [best_paths_axis, worst_paths_axis]
    helpers.save_subfigure_plot("best-and-worst-paths-cdf.pdf", axis_to_plot, no_legend=True)

def plot_share_delay_cdf_across_ks(packet_info_dir):
    """
    Generate share delay cumulative distribution function plots for a fixed set of K values.
    """
    k_to_packets = {}
    for k_value in range(3, 9):
        packets_file_path = packet_info_dir.joinpath(path.Path("packet-dump-info-%d.txt" % k_value))
        k_to_packets[k_value] = read_packet_dump_info_from_file(packets_file_path)

    for plot_idx, (k_value, packets) in enumerate(k_to_packets.items()):
        plot_share_delay_cdf(packets, label="$K$=%d" % k_value, idx=plot_idx)

    title_string = helpers.title_font(
         r"$n=10$, $\lambda=50$, $\delta=100ms$, $latency=\mathcal{U}(0ms, 250ms)$, $jitter=50ms$")
    plt.title(title_string)
    plt.xlabel(r"Inter-share delay ($ms$)")
    plt.ylabel(r"$\mathbb{P}\{x < \mathcal{X}\}$")
    helpers.save_figure("share-delay-cdf.pdf", num_cols=len(k_to_packets))

def generate_active_paths_per_interval_plot(set_of_traces_to_plot, trace_names):
    """
    Generate a plot of the probability density function of the number of active paths
    per \delta ms interval. A path is defined as being active if it is carrying 
    shares for any sequence number.
    """
    bar_width = 0.35
    possible_x_values = set()
    for bar_idx, (trace_name, packets) in enumerate(zip(trace_names, set_of_traces_to_plot)):
        packets = sorted(packets, key=lambda p_i: p_i.timestamp)
        delta = 100 * 10**3 # microseconds
        interval_start  = packets[0].timestamp
        current_time    = packets[0].timestamp

        active_ports_in_interval = set()
        number_of_active_paths_per_interval = []
        for p_i in packets:
            current_time = p_i.timestamp
            if (current_time - interval_start) > delta:
                number_of_active_paths_per_interval.append(len(active_ports_in_interval))
                active_ports_in_interval = set()
                interval_start = current_time

            active_ports_in_interval.add((p_i.source_port, p_i.destination_port))
        

        counted_data = list(Counter(number_of_active_paths_per_interval).items())
        hist_data_for_trace = sorted(counted_data,
            key=lambda kvp_i: kvp_i[0])
        possible_x_values = possible_x_values | set([t_i[0] for t_i in hist_data_for_trace])
        vector_sum = sum([t_i[1] for t_i in hist_data_for_trace])
        normed_hist_data_for_trace = [t_i[1] / vector_sum for t_i in hist_data_for_trace]

        bar_x_locations = [t_i[0] + (bar_width * bar_idx) for t_i in hist_data_for_trace]
        helpers.plot_a_bar(bar_x_locations, normed_hist_data_for_trace, 
                idx=bar_idx, bar_width=bar_width, label=trace_name)
        
    x_tick_labels       = list(sorted(possible_x_values))
    x_tick_locations = [x_i + ((bar_width/2) * (len(set_of_traces_to_plot)-1)) for x_i in 
            x_tick_labels]
    plt.xticks(x_tick_locations, x_tick_labels)
    plt.xlabel(r"Number of active paths per $\delta$ ms")
    plt.ylabel(r"$\mathbb{P}\{x = \mathcal{X}\}$")
    helpers.save_figure("active-paths-histogram.pdf", num_cols=len(set_of_traces_to_plot))

def generate_number_of_time_periods_shares_were_active_pdf(set_of_traces_to_plot, trace_names):
    """
    Generate a plot of the probability density function of the number of \delta ms time
    periods that shares for a particular sequence number were present in the network. A single
    PDF is generated and plotted for each ofthe traces in <set_of_traces_to_plot>.
    """
    pass

def generate_all_plots():
    K_VALUE                         = 5
    BASE_PACKET_INFO_DIR            = path.Path("/home/cpsc-net-user/repos/data-files/")
    UNIFORM_250_PACKET_INFO_DIR     = BASE_PACKET_INFO_DIR / path.Path("uniform-250")
    DISCRETE_PACKET_INFO_DIR        = BASE_PACKET_INFO_DIR / path.Path("discrete")
    packet_dump_info_file           = path.Path("packet-dump-info-%d.txt" % K_VALUE)

    uniform_packets = read_packet_dump_info_from_file(
            UNIFORM_250_PACKET_INFO_DIR / packet_dump_info_file)
    discrete_packets = read_packet_dump_info_from_file(
            DISCRETE_PACKET_INFO_DIR / packet_dump_info_file)

    # plot_share_delay_histogram(packet_dump_info)
    # plot_share_delay_cdf_across_ks(PACKET_INFO_DIR)
    # plot_best_and_worst_paths_cdf(PACKETS)
    captures_to_plot = [uniform_packets, discrete_packets]
    generate_active_paths_per_interval_plot(captures_to_plot, ["uniform", "discrete"])













