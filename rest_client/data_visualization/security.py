
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot                        as plt
import pathlib                                  as path
import pprint                                   as pp
import itertools                                as itertools
import numpy                                    as np

import data_visualization.params                as cfg
import data_visualization.helpers               as helpers

from collections                    import namedtuple, defaultdict

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
    def configure_plot():
        plt.xlim((0, 300))
        plt.xlabel("Inter-share delay")
        plt.ylabel(r"$\mathbb{P}\{x < \mathcal{X}\}$")
        title_string = helpers.title_font(
             r"$N=9$, $K=5$, $\lambda=50$, $\delta=100ms$, $latency=\mathcal{U}(0ms, 250ms)$, $jitter=50ms$")
        plt.title(title_string)
        plt.axvline(x=250, color="red", linestyle="--")

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


    sorted_paths = sorted([(port_key, inter_share_delays) 
            for port_key, inter_share_delays in port_group_to_isd.items()],
            key=lambda t_i: np.mean(t_i[1]))
    best_paths = sorted_paths[:5]
    worst_paths = sorted_paths[len(sorted_paths)-5:]
    for plot_idx, (port_group, inter_share_delays) in enumerate(best_paths):
        helpers.plot_a_cdf(sorted(inter_share_delays), idx=plot_idx, plot_markers=False)

    configure_plot()
    helpers.save_figure("best-paths-cdf.pdf", no_legend=True)

    for plot_idx, (port_group, inter_share_delays) in enumerate(worst_paths):
        helpers.plot_a_cdf(sorted(inter_share_delays), idx=plot_idx, plot_markers=False)

    configure_plot()
    helpers.save_figure("worst-paths-cdf.pdf", no_legend=True)

def plot_share_delay_cdf_across_ks(packet_info_dir):
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

def generate_all_plots():
    PACKET_INFO_DIR = path.Path("/home/cpsc-net-user/repos/data-files/")
    K_VALUE         = 5
    PACKETS_PATH    = path.Path("/home/cpsc-net-user/repos/data-files/packet-dump-info-%d.txt" %
            K_VALUE)
    PACKETS         = read_packet_dump_info_from_file(PACKETS_PATH)
    # pp.pprint(packet_dump_info)

    # plot_share_delay_histogram(packet_dump_info)
    # plot_share_delay_cdf_across_ks(PACKET_INFO_DIR)
    plot_best_and_worst_paths_cdf(PACKETS)













