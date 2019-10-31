
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot            as plt
import numpy                        as np
import json                         as json
import pathlib                      as path
import pprint                       as pp
import random                       as rand

import data_visualization.params            as cfg
import data_visualization.helpers           as helpers
import path_hopping.params                  as ph_cfg   
import nw_control.results_repository        as rr

from collections                            import defaultdict, Counter

FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

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

DEFAULT_SEED_NUMBER = 0xCAFE_BABE
seed_number = DEFAULT_SEED_NUMBER
# seed_number = rand.randint(0, 2**32)
np.random.seed(seed_number)

def display_capture_statistics(trial_provider):
    for trial in trial_provider:
        captured_packets = trial.get_parameter("packet-dump")
        print("Capture has %d packets" % len(captured_packets))
        port_set = {p_i.destination_port for p_i in captured_packets}
        print("Capture has %d unique source ports" % len(port_set))
        pp.pprint(port_set)

def fixed_attacker(packets, K):
    ports = list({p_i.source_port 
        for p_i in packets if (p_i.source_port != 11111) and (p_i.source_ip == "10.10.0.1")})
    ports_to_listen_on = np.random.choice(ports, K, replace=False)
    seq_num_to_share_count = defaultdict(int)
    print("K = %d" % K)
    for p_i in packets:
        if p_i.source_ip == "10.10.0.1" and p_i.source_port in ports_to_listen_on:
            seq_num_to_share_count[p_i.seq_num] += 1
    pp.pprint(Counter(seq_num_to_share_count.values()))
    return len([s_i for s_i in seq_num_to_share_count.values() if s_i == K])

def random_attacker(packets, K, timestep_ms, duration):
    print("Performing random attack on trace with K = %d, timestep = %d and duration = %f" %
            (K, timestep_ms, duration))
    ports = list({p_i.source_port 
        for p_i in packets if (p_i.source_port != 11111) and (p_i.source_ip == "10.10.0.1")})
    # print(ports)
    ports_to_listen_on = np.random.choice(ports, K, replace=False)
    seq_num_to_share_count = defaultdict(list)
    interval_start_time = packets[0].timestamp
    interval_id = 0
    number_of_packets_from_sender = 0
    for p_i in packets:
        if p_i.source_ip == "10.10.0.1":
            number_of_packets_from_sender += 1

        if p_i.source_ip == "10.10.0.1" and p_i.source_port in ports_to_listen_on:
            seq_num_to_share_count[p_i.seq_num].append((p_i.share_num, interval_id))
        
        if (p_i.timestamp - interval_start_time) > (timestep_ms * 1000):
            interval_id += 1
            interval_start_time = p_i.timestamp
            ports_to_listen_on = np.random.choice(ports, K, replace=False)
    
    # print("Number of messages transmitted by the sender %d" % len(seq_num_to_share_count))
    # print("Examined %d packets from the sender." % number_of_packets_from_sender)
    print("Unsynchronized random attacker hopped %d times." % interval_id)
    return len([s_i for s_i in seq_num_to_share_count.values() 
        if len(s_i) == K
        # and all([t_i[1] == s_i[0][1] for t_i in s_i])
        ])

def perturbed_random_attacker(packets, K, timestep_ms, duration):
    print(f"Performing random perturbed attack on trace with K = {K}, "\
            "timestep = {timestep_ms} and duration = {duration}")
    timestep_us = timestep_ms * 1000
    ports = list({p_i.source_port
        for p_i in packets if (p_i.source_port != 11111) and (p_i.source_ip == "10.10.0.1")})
    ports_to_listen_on = np.random.choice(ports, K, replace=False)
    seq_num_to_share_count = defaultdict(list)
    interval_start_time = packets[0].timestamp
    interval_id = 0
    number_of_packets_from_sender = 0
    perturbation_factor = np.random.uniform(-0.5, 0.5)
    for p_i in packets:
        if p_i.source_ip == "10.10.0.1":
            number_of_packets_from_sender += 1

        if p_i.source_ip == "10.10.0.1" and p_i.source_port in ports_to_listen_on:
            seq_num_to_share_count[p_i.seq_num].append((p_i.share_num, interval_id))

        if (p_i.timestamp - interval_start_time) > \
                (timestep_us + (timestep_us * perturbation_factor)):
            interval_id += 1
            interval_start_time = p_i.timestamp
            ports_to_listen_on = np.random.choice(ports, K, replace=False)
            perturbation_factor = np.random.uniform(-0.5, 0.5)

    return len([s_i for s_i in seq_num_to_share_count.values()
        if len(s_i) == K
        ])

def synchronized_random_attacker(packets, sender_hop_times, K, timestep_ms):
    print(len(sender_hop_times))
    ports = list({p_i.source_port
        for p_i in packets if (p_i.source_port != 11111) and (p_i.source_ip == "10.10.0.1")})
    ports_to_listen_on = np.random.choice(ports, K, replace=False)
    seq_num_to_share_count = defaultdict(list)
    interval_start_time = packets[0].timestamp
    interval_id = 0
    hop_time_index = 0
    for p_i in packets:
        if hop_time_index < len(sender_hop_times) and \
                p_i.timestamp >= sender_hop_times[hop_time_index]:
            hop_time_index += 1
            ports_to_listen_on = np.random.choice(ports, K, replace=False)

        if p_i.source_ip == "10.10.0.1" and p_i.source_port in ports_to_listen_on:
            seq_num_to_share_count[p_i.seq_num].append((p_i.share_num, interval_id))

    print("Synchronized random attacker hopped %d times" % hop_time_index)
    return len([s_i for s_i in seq_num_to_share_count.values()
        if len(s_i) == K
        ])
    
def print_capture_statistics(trial):
    packets = trial.get_parameter("packet-dump")
    pp.pprint(Counter(Counter([p_i.seq_num for p_i in packets if p_i.source_ip == "10.10.0.1"]).values()))

def display_statistics_for_fixed_attacker(trial_provider):
    for trial in trial_provider:
        captured_packets = trial.get_parameter("packet-dump")
        print(len(captured_packets))
        recovered_messages = fixed_attacker(captured_packets, trial.get_parameter("K"))
        print("The fixed attacker recovered %d messages." % recovered_messages)

def display_statistics_for_random_attacker(trial_provider):
    for trial in trial_provider:
        captured_packets = trial.get_parameter("packet-dump")
        recovered_messages = random_attacker(captured_packets, trial.get_parameter("K"),
                trial.get_parameter("timestep"), trial.get_parameter("elapsed-tx-time"))
        print("The unsynchronized random attacker recovered %d messages." % recovered_messages)

def display_statistics_for_synchronized_random_attacker(trial_provider):
    for trial in trial_provider:
        captured_packets = trial.get_parameter("packet-dump")
        recovered_messages = synchronized_random_attacker(captured_packets,
                trial.get_parameter("hopping-times"), trial.get_parameter("K"), 
                trial.get_parameter("timestep"))
        print("The synchronized random attacker recovered %d messages." % recovered_messages)

def display_active_paths_per_interval(trial, interval_duration):
    packets = trial.get_parameter("packet-dump")
    active_paths_per_interval = []
    interval_start_time = packets[0].timestamp
    ports_in_interval = set()
    for p_i in packets:
        if (p_i.timestamp - interval_start_time) > interval_duration:
            interval_start_time = p_i.timestamp
            active_paths_per_interval.append(len(ports_in_interval))
            ports_in_interval = set()

        if p_i.source_ip == "10.10.0.1":
            ports_in_interval.add(p_i.source_port)

    pp.pprint({k: v/len(active_paths_per_interval) 
        for k, v in Counter(active_paths_per_interval).items()})

def generate_data_recovery_data(trial_provider, independent_variable):
    random_attacker_scatter_points              = defaultdict(list)
    fixed_attacker_scatter_points               = defaultdict(list)
    random_synced_attacker_scatter_points       = defaultdict(list)
    random_perturbed_attacker_scatter_points    = defaultdict(list)
    unique_seq_nums = None
    for the_trial in trial_provider:
        packets             = the_trial.get_parameter("packet-dump")
        x_value             = the_trial.get_parameter(independent_variable)
        k_value             = the_trial.get_parameter("K")
        timestep            = the_trial.get_parameter("timestep")
        sender_hop_times    = the_trial.get_parameter("hopping-times")
        elapsed_tx_time     = the_trial.get_parameter("elapsed-tx-time") 

        for round_seed_number in [rand.randint(0, 2**32) for _ in range(10)]:
            unique_seq_nums = len({p_i.seq_num for p_i in packets if p_i.source_ip == "10.10.0.1"})

            packets_at_receiver = [p_i for p_i in packets if p_i.source_ip == "10.10.0.1"]
            random_attacker_recovered_packets = random_attacker(packets_at_receiver, 
                    k_value, timestep, elapsed_tx_time)
            fixed_attacker_recovered_packets = fixed_attacker(packets_at_receiver, k_value)
            random_synced_recovered_packets = synchronized_random_attacker(packets_at_receiver,
                    sender_hop_times, k_value, timestep)
            random_perturbed_recovered_packets = perturbed_random_attacker(
                    packets_at_receiver, k_value, timestep, elapsed_tx_time)

            random_attacker_scatter_points[x_value].append(random_attacker_recovered_packets)
            fixed_attacker_scatter_points[x_value].append(fixed_attacker_recovered_packets)
            random_synced_attacker_scatter_points[x_value].append(random_synced_recovered_packets)
            random_perturbed_attacker_scatter_points[x_value].append(
                    random_perturbed_recovered_packets)
    
    random_unsynchronized_attacker_data = [
            (iv_value, np.mean(recovered_packets), np.std(recovered_packets))
        for iv_value, recovered_packets in random_attacker_scatter_points.items()]

    fixed_attacker_data = [
            (iv_value, np.mean(recovered_packets), np.std(recovered_packets))
            for iv_value, recovered_packets in fixed_attacker_scatter_points.items()]
    
    random_synchronized_attacker_data = [
            (iv_value, np.mean(recovered_packets), np.std(recovered_packets))
            for iv_value, recovered_packets in random_synced_attacker_scatter_points.items()]

    random_perturbed_attacker_data = [
            (iv_value, np.mean(recovered_packets), np.std(recovered_packets))
            for iv_value, recovered_packets in random_perturbed_attacker_scatter_points.items()]

    trial_provider.add_metadata("random-unsynchronized-attacker-data",
            random_unsynchronized_attacker_data)
    trial_provider.add_metadata("fixed-attacker-data", fixed_attacker_data)
    trial_provider.add_metadata("random-synchronized-attacker-data",
            random_synchronized_attacker_data)
    trial_provider.add_metadata("random-perturbed-attacker-data",
            random_perturbed_attacker_data)

    results_repository = rr.ResultsRepository.create_repository(ph_cfg.base_repository_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    schema_vars = {"provider-name": (trial_provider.provider_name + "-computed")}
    results_repository.write_trial_provider(schema_vars, trial_provider, overwrite=True)

def xs(ts):
    return [t_i[0] for t_i in ts]
def ys(ts):
    return [t_i[1] for t_i in ts]
def zs(ts):
    return [t_i[2] for t_i in ts]

def generate_data_recovery_versus_k_scatter(trial_provider):
    random_unsynchronized_attacker_data = trial_provider.get_metadata(
            "random-unsynchronized-attacker-data")
    fixed_attacker_data = trial_provider.get_metadata("fixed-attacker-data")
    random_synchronized_attacker_data = trial_provider.get_metadata(
            "random-synchronized-attacker-data")
    random_perturbed_attacker_data = trial_provider.get_metadata("random-perturbed-attacker-data")

    packets = next(iter(trial_provider)).get_parameter("packet-dump")
    packets = [t_i.get_parameter("packet-dump") for t_i in trial_provider]
    unique_seq_nums = max([
        len({p_i.seq_num for p_i in packets_i if p_i.source_ip == "10.10.0.1"})
        for packets_i in packets
        ])
    # unique_seq_nums = len({p_i.seq_num for p_i in packets if p_i.source_ip == "10.10.0.1"})

    fig, ax = plt.subplots()

    helpers.plot_a_scatter(xs(random_unsynchronized_attacker_data), 
            ys(random_unsynchronized_attacker_data),
            idx=0, label="Random Unsynchronized Attacker", 
            err=zs(random_unsynchronized_attacker_data),
            axis_to_plot_on=ax)
    # helpers.plot_a_scatter(xs(fixed_attacker_data), 
    #         ys(fixed_attacker_data),
    #         idx=1, label="Fixed Attacker", err=zs(fixed_attacker_data),
    #         axis_to_plot_on=ax)
    # helpers.plot_a_scatter(xs(random_synchronized_attacker_data), 
    #         ys(random_synchronized_attacker_data), idx=2, label="Random Synchronized Attacker", 
    #         err=zs(random_synchronized_attacker_data),
    #         axis_to_plot_on=ax)
    helpers.plot_a_scatter(xs(random_perturbed_attacker_data),
            ys(random_perturbed_attacker_data), idx=1, label="Random Perturbed Attacker",
            err=zs(random_perturbed_attacker_data),
            axis_to_plot_on=ax)
    helpers.plot_a_scatter([1, 9], [unique_seq_nums]*2, label="Total Messages",
            plot_markers=False, idx=2,
            axis_to_plot_on=ax)

    inset_axis = ax.inset_axes([0.05, 0.5, 0.47, 0.37])
    x1, x2, y1, y2 = 0.5, 8.5, -10, 30000
    inset_axis.set_xlim(x1, x2)
    inset_axis.set_ylim(y1, y2)
    inset_axis.set_xticklabels("")
    inset_axis.set_yticklabels("")

    helpers.plot_a_scatter(xs(random_unsynchronized_attacker_data), 
            ys(random_unsynchronized_attacker_data),
            idx=0, label="Random Unsynchronized Attacker", 
            err=zs(random_unsynchronized_attacker_data),
            axis_to_plot_on=inset_axis)
    # helpers.plot_a_scatter(xs(fixed_attacker_data), 
    #         ys(fixed_attacker_data),
    #         idx=1, label="Fixed Attacker", err=zs(fixed_attacker_data),
    #         axis_to_plot_on=inset_axis)
    # helpers.plot_a_scatter(xs(random_synchronized_attacker_data), 
    #         ys(random_synchronized_attacker_data), idx=2, label="Random Synchronized Attacker", 
    #         err=zs(random_synchronized_attacker_data),
    #         axis_to_plot_on=inset_axis)
    helpers.plot_a_scatter(xs(random_perturbed_attacker_data),
            ys(random_perturbed_attacker_data), idx=1, label="Random Perturbed Attacker",
            err=zs(random_perturbed_attacker_data),
            axis_to_plot_on=inset_axis)

    ax.indicate_inset_zoom(inset_axis, label=None)

    helpers.xlabel("$K$")
    helpers.ylabel("\# of Recovered Messages.")
    helpers.save_figure("attacker-data-recovery-vs-k.pdf", num_cols=2)

def generate_data_recovery_versus_delta_scatter(trial_provider):
    random_unsynchronized_attacker_data = trial_provider.get_metadata(
            "random-unsynchronized-attacker-data")
    fixed_attacker_data = trial_provider.get_metadata("fixed-attacker-data")
    random_synchronized_attacker_data = trial_provider.get_metadata(
            "random-synchronized-attacker-data")

    packets = next(iter(trial_provider)).get_parameter("packet-dump")
    unique_seq_nums = len({p_i.seq_num for p_i in packets if p_i.source_ip == "10.10.0.1"})

    helpers.plot_a_scatter(xs(random_unsynchronized_attacker_data), 
            ys(random_unsynchronized_attacker_data),
            idx=0, label="Random Unsynchronized Attacker", 
            err=zs(random_unsynchronized_attacker_data))
    helpers.plot_a_scatter(xs(fixed_attacker_data), 
            ys(fixed_attacker_data),
            idx=1, label="Fixed Attacker", err=zs(fixed_attacker_data))
    helpers.plot_a_scatter(xs(random_synchronized_attacker_data), 
            ys(random_synchronized_attacker_data), idx=2, 
            label="Random Synchronized Attacker", 
            err=zs(random_synchronized_attacker_data))
    helpers.plot_a_scatter([min(xs(fixed_attacker_data)), max(xs(fixed_attacker_data))], 
            [unique_seq_nums]*2, label="Total Messages", plot_markers=False, idx=3)

    helpers.xlabel(r"$\delta$")
    helpers.ylabel(r"\# of Recovered Messages.")
    helpers.save_figure("attacker-data-recovery-vs-delta.pdf", num_cols=2)
