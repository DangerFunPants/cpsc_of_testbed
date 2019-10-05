
import traceback                        as traceback
import networkx                         as nx
import time                             as time
import pathlib                          as path

import virtual_hosts.virtual_host       as virtual_host
import nw_control.topo_mapper           as topo_mapper
import attacker_tests.trials            as trials
import nw_control.packet_capture        as pcap
import nw_control.stat_monitor          as stat_monitor
import nw_control.params                as cfg
import nw_control.results_repository    as rr
import path_hopping.params              as ph_cfg

from collections                        import defaultdict

SUBSTRATE_TOPOLOGY = nx.complete_graph(10)

def compute_link_key(source_id, destination_id):
    return tuple(sorted((source_id, destination_id)))

def compute_link_utilization_over_time(link_byte_counts):
    """
    Compute a list of sampled link utilization values based on 
    the byte count samples retrieved from the stat_monitor module.

    link_byte_counts: [byte_count_snapshots]
    byte_count_snapshot: (sourceSwitchId, destinationSwitchId, bytesReceived, bytesSent)

    RETURNS 
        tx_rate_t: (source_id x destination_id) -> link_utilization_in_time_period_t forall. t
    """
    def find_matching_iface_stats(byte_count, source_id, destination_id):
        matching_stats = [d_i for d_i in byte_count
                if d_i["sourceSwitchId"] == source_id and
                d_i["destinationSwitchId"] == destination_id]
        if len(matching_stats) != 1:
            raise ValueError("Unexpected results in find_matching_iface_stats. \
                    Found %d matching iface_stats" % len(matching_stats))
        return matching_stats[0]

    def compute_tx_rate(count_in_bytes):
        return (count_in_bytes * 8) / 10.0**7

    # First compute the delta between the iface_stats in time_period t_i and the iface_stats
    # in time period t_{i+1}.
    # tx_rate_t: (source_id x destination_id) -> link_utilization_in_time_period_t forall. t
    tx_rate_t = []
    for t_0, t_1 in zip(link_byte_counts, link_byte_counts[1:]):
        byte_count_delta_t = defaultdict(float)
        for iface_stats in t_0:
            source_id = iface_stats["sourceSwitchId"]
            destination_id = iface_stats["destinationSwitchId"]
            t_0_count = iface_stats["bytesSent"] + iface_stats["bytesReceived"]
            try:
                t_1_stats = find_matching_iface_stats(t_1, source_id, destination_id)
                t_1_count = t_1_stats["bytesSent"] + t_1_stats["bytesReceived"]
            except ValueError:
                t_1_count = t_0_count

            count_delta = t_1_count - t_0_count
            link_key = compute_link_key(source_id, 
                    destination_id)
            byte_count_delta_t[link_key] += count_delta

        tx_rate_t.append({the_link_key: compute_tx_rate(byte_count_t) 
            for the_link_key, byte_count_t in byte_count_delta_t.items()})
    return tx_rate_t

def destroy_sender_receiver_pair(sender, receiver):
    if sender != None:
        sender.destroy_virtual_host()
    else:
        print("Refusing to destroy non-existent sender!")

    if receiver != None:
        receiver.destroy_virtual_host()
    else:
        print("Refusing to destroy non-existent receiver!")

def create_sender_receiver_pair(id_to_dpid):
    CREATE_VHOST_RETRY_COUNT    = 1
    virtual_host_mac_address    = "00:02:00:00:00:%02d"
    actual_host_ip_address      = "192.168.1.%d"
    virtual_host_ip_address     = "10.10.0.%d"

    sender_host_id      = 1
    receiver_host_id    = 2

    sender_host = None
    receiver_host = None
    last_ex = None
    for _ in range(CREATE_VHOST_RETRY_COUNT):
        try:
            sender_host = virtual_host.PathHoppingSender.create_virtual_host(sender_host_id, 
                        (virtual_host_mac_address % sender_host_id),
                        (virtual_host_ip_address % sender_host_id),
                        (actual_host_ip_address % sender_host_id),
                        id_to_dpid[sender_host_id - 1])

            receiver_host = virtual_host.PathHoppingReceiver.create_virtual_host(receiver_host_id,
                    (virtual_host_mac_address % receiver_host_id),
                    (virtual_host_ip_address % receiver_host_id),
                    (actual_host_ip_address % receiver_host_id),
                    id_to_dpid[receiver_host_id - 1])
        except Exception as ex:
            destroy_sender_receiver_pair(sender_host, receiver_host)
            last_ex = ex

    if sender_host == None or receiver_host == None:
        raise last_ex

    return sender_host, receiver_host

def conduct_path_hopping_trial(results_repository, the_trial):
    def stringify(value):
        return value if type(value) == str else str(value)

    def get_sender_kwargs(the_trial):
        sender_kwargs = { "port"            : the_trial.get_parameter("port")
                        , "K"               : the_trial.get_parameter("K")
                        , "N"               : the_trial.get_parameter("N")
                        , "data_file"       : the_trial.get_parameter("input-file")
                        , "message_size"    : the_trial.get_parameter("message-size")
                        , "timestep"        : the_trial.get_parameter("timestep")
                        , "hop_probability" : the_trial.get_parameter("lambda")
                        , "reliable"        : the_trial.get_parameter("reliable")
                        , "hop_method"      : the_trial.get_parameter("hop")
                        }
        sender_kwargs = {kw: stringify(arg) for kw, arg in sender_kwargs.items()}
        return sender_kwargs

    def get_receiver_kwargs(the_trial, sender_ip):
        receiver_kwargs = { "sender_ip"             : sender_ip
                          , "port"                  : the_trial.get_parameter("port")
                          , "data_file"             : the_trial.get_parameter("output-file")
                          , "timestep"              : the_trial.get_parameter("timestep")
                          , "hopping_probability"   : the_trial.get_parameter("lambda")
                          }
        receiver_kwargs = {kw: stringify(arg) for kw, arg in receiver_kwargs.items()}
        return receiver_kwargs

    def collect_mpc_sender_hopping_times():
        hopping_times_record_path = path.Path("./hopping-time-record.txt")
        hopping_times_text = hopping_times_record_path.read_text()
        hopping_times = [int(s_i) for s_i in hopping_times_text.splitlines()]
        hopping_times_record_path.unlink()
        return hopping_times

    sender, receiver, packet_capture = None, None, None
    try:
        id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(SUBSTRATE_TOPOLOGY)

        sender, receiver = create_sender_receiver_pair(id_to_dpid)
        time.sleep(10)

        packet_capture = pcap.InterfaceCapture("ens192")
        traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)

        packet_capture.start_capture()
        traffic_monitor.start_monitor()

        sender.start_path_hopping_sender(**get_sender_kwargs(the_trial))

        start_time = time.time()
        receiver.start_path_hopping_receiver(
                **get_receiver_kwargs(the_trial, sender.virtual_host_ip))
    
        print("Waiting on the receiver to terminate...")
        receiver.wait_until_done()
        end_time = time.time()
        print("Receiver has terminated.")
        elapsed_tx_time = end_time - start_time
        traffic_monitor.stop_monitor()
        utilization_results = traffic_monitor.get_monitor_statistics()

        packet_capture.stop_capture()
        packets = packet_capture.process_capture_data()
        
        hopping_times = collect_mpc_sender_hopping_times()
        print("Captured %d packets" % len(packets))

        the_trial.add_parameter("packet-dump", packets)
        the_trial.add_parameter("measured-link-utilization", utilization_results)
        the_trial.add_parameter("link-utilization-over-time",
                compute_link_utilization_over_time(utilization_results))
        the_trial.add_parameter("elapsed-tx-time", elapsed_tx_time)
        the_trial.add_parameter("hopping-times", hopping_times)
    except Exception as ex:
        traceback.print_exc()
        print(ex)
        input("Failed to carry out path hopping attacker test. Press enter to continue...")
    finally:
        destroy_sender_receiver_pair(sender, receiver)
        if packet_capture != None and packet_capture.is_capture_running():
            packet_capture.stop_capture()

def test_virtual_host_installation():
    id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(SUBSTRATE_TOPOLOGY)
    sender, receiver = None, None
    while True:
        try:
            sender, receiver = create_sender_receiver_pair(id_to_dpid)
        except Exception as ex:
            print(ex)
            print("Failed to create sender or receiver")

        try:
            destroy_sender_receiver_pair(sender, receiver)
        except Exception:
            pass
        input("Press enter to try again.") 

def main():
    results_repository = rr.ResultsRepository.create_repository(ph_cfg.base_repository_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)

    # trial_provider = trials.test_with_single_trial()
    # trial_provider = trials.test_with_varying_k_values()
    trial_provider = trials.test_with_varying_delta_values()

    for the_trial in trial_provider:
        print("Conducting trial with K = %d" % the_trial.get_parameter("K"))
        conduct_path_hopping_trial(None, the_trial)
        time.sleep(10)

    schema_vars = {"provider-name": trial_provider.provider_name}
    results_repository.write_trial_provider(schema_vars, trial_provider, overwrite=True)

if __name__ == "__main__":
    main()
