
import pathlib              as path
import time                 as time
import json                 as json
import pprint               as pp

import nw_control.host                  as host
import nw_control.host_mapper           as host_mapper
import nw_control.params                as cfg
import mp_routing.params                as mp_cfg
import mp_routing.file_parsing          as fp
import mp_routing.onos_route_adder      as onos
import mp_routing.vle_trial             as vle_trial
import nw_control.stat_monitor          as stat_monitor
import nw_control.results_repository    as rr
import traffic_analysis.core_taps       as core_taps

from collections        import defaultdict
from datetime           import datetime

ABILENE_TOPO_FILE_PATH = path.Path("./abilene.txt")

def create_and_initialize_host_connections(route_adder, mapper):
    od_pairs = route_adder.get_src_dst_pairs()
    host_ids = {src for (src, _) in od_pairs} | {dst for (_, dst) in od_pairs}
    hosts = {}

    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = host.TrafficGenHost.create_host(hostname, host_id)
        hosts[host_id].connect()

    return hosts

def collect_end_host_results(hosts):
    results_map = {}
    for host_id, host in hosts.items():
        receiver_results, sender_results = host.retrieve_end_host_results()
        results_dict = { "receiver"     : receiver_results
                       , "sender"       : sender_results
                       }
        results_map[host_id] = results_dict
    return results_map

def process_end_host_results(the_vle_trial, end_host_results, mapper):
    # processed_results = defaultdict(dict) 
    used_source_ports = defaultdict(set)
    processed_results = defaultdict(lambda: defaultdict(list))
    for flow_id, flow in enumerate(the_vle_trial.solver_results.flows):
        source_node         = flow.source_node
        destination_node    = flow.destination_node
        destination_ip      = mapper.get_ip_address_for_host_number(destination_node)
        source_ip           = mapper.get_ip_address_for_host_number(source_node)
         
        try:
            sender_results = next(results_dict
                    for results_dict in end_host_results[source_node]["sender"].values()
                    if results_dict["dst_ip"] == destination_ip and
                    results_dict["src_port"] not in used_source_ports[source_node])
        except StopIteration:
            print("Failed to find sender results for %d -> %d" %
                    (source_node, destination_node))
            processed_results[source_node][destination_node].append(None)
            continue

        try:
            receiver_results = next(results_list
                    for results_list in end_host_results[destination_node]["receiver"]
                    if results_list[0] == source_ip and 
                    results_list[1] == sender_results["src_port"])
        except StopIteration:
            print("Failed to find receiver results for %d -> %d" %
                    (source_node, destination_node))
            processed_results[source_node][destination_node].append(None)
            continue
        packet_counts = (sender_results["pkt_count"], receiver_results[2])
        count_dict = { "receiver-count"     : packet_counts[1]
                     , "sender-count"       : packet_counts[0]
                     }
        processed_results[source_node][destination_node].append(count_dict)
        used_source_ports[source_node].add(sender_results["src_port"])

    # sender_results = {node_id: end_host_results[node_id]["sender"] 
    #         for node_id in end_host_results.keys()}
    # receiver_results = {node_id: end_host_results[node_id]["receiver"]
    #         for node_id in end_host_results.keys()}
    # for 
    return dict({k: dict(v) for k, v in processed_results.items()})

def close_all_host_connections(hosts):
    for host in hosts.values():
        host.disconnect()

def conduct_onos_trial(the_vle_trial, route_adder, trial_length, results_repository):
    # remove_all_count_files(route_adder)
    mapper = host_mapper.OnosMapper(cfg.dns_server_ip, cfg.of_controller_ip, 
            cfg.of_controller_port, ABILENE_TOPO_FILE_PATH.read_text())

    hosts = create_and_initialize_host_connections(route_adder, mapper)
    for host_id, host in hosts.items():
        host.start_server()
    
    time.sleep(5)

    tag_values = route_adder.install_routes()
    for flow_id, flow in enumerate(route_adder.get_flows()):
        src_host        = flow.source_node
        dst_host        = flow.destination_node
        path_split      = [p_i.fraction for p_i in flow.paths]
        mu              = flow.rate
        sigma           = flow.variance
        rate_list       = [(r_i/8)*10**6 for r_i in flow.actual_tx_rates]
        
        dst_hostname    = mapper.map_sw_to_host(dst_host)
        dst_ip          = mapper.resolve_hostname(dst_hostname)
        print("flow: %s -> %s (%s)" % (src_host, dst_host, mu))
        # hosts[src_host].configure_client(mu, sigma, mp_cfg.traffic_model,
        #         dst_ip, mp_cfg.dst_port, path_split, src_host, mp_cfg.time_slice,
        #         tag_values[flow_id])

        hosts[src_host].configure_precomputed_client(rate_list, dst_ip, mp_cfg.dst_port,
                path_split, src_host, mp_cfg.time_slice, tag_values[flow_id])

    od_pairs = route_adder.get_src_dst_pairs()
    for source_node in set((s for (s, _) in od_pairs)):
        hosts[source_node].start_clients()

    traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
    traffic_monitor.start_monitor()

    # time.sleep(trial_length)
    input("Press enter to continue...")
    # time.sleep(120)
    traffic_monitor.stop_monitor()

    for source_node in set((s for (s, _) in od_pairs)):
        hosts[source_node].stop_client()

    # time.sleep(15)

    for host_id in hosts:
        hosts[host_id].stop_server()

    time.sleep(10)

    utilization_results = traffic_monitor.get_monitor_statistics()
    utilization_json    = json.dumps(utilization_results)

    end_host_results        = collect_end_host_results(hosts)
    processed_results       = process_end_host_results(the_vle_trial, end_host_results, mapper)
    end_host_results_json   = json.dumps(processed_results)

    route_adder.remove_routes()
    close_all_host_connections(hosts)

    schema_vars = { "trial-name"    : "test-trial"
                  , "trial-type"     : "link-embedding"
                  }

    results_files = { "utilization-results.txt"     : utilization_json
                    , "vle-trial.json"              : vle_trial.VleTrial.to_json(the_vle_trial)
                    , "end-host-results.json"       : end_host_results_json
                    }

    results_repository.write_trial_results(schema_vars, results_files)


def main():
    def build_file_path(route_files_dir, trial_name, seed_no):
        return route_files_dir / trial_name / path.Path("seed_%s" % seed_no)

    mapper = host_mapper.OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, 
            cfg.of_controller_port, ABILENE_TOPO_FILE_PATH.read_text())
    seed_no         = "4065"
    mu              = mp_cfg.mu
    sigma           = mp_cfg.sigma
    trial_path = build_file_path(path.Path(mp_cfg.var_rate_route_path),
            "prob_mean_1_sigma_1.0", seed_no)

    tx_rate_list, mean_flow_tx_rates, std_dev_flow_tx_rates = core_taps.get_rates_for_flows()
    the_trial = vle_trial.VleTrial.create_trial(mean_flow_tx_rates, std_dev_flow_tx_rates,
            tx_rate_list, 4065)

    pp.pprint(the_trial.solver_results)

    route_provider          = the_trial.solver_results
    route_adder             = onos.OnosRouteAdder(route_provider, mapper)
    results_repository      = rr.ResultsRepository.create_repository(mp_cfg.base_repository_path, 
            mp_cfg.repository_schema, mp_cfg.repository_name)

    try:
        conduct_onos_trial(the_trial, route_adder, 60, results_repository)
    except Exception as ex:
        print("Failed to conduct onos_trial")
        print(ex)
        route_adder.remove_routes()
        raise ex

if __name__ == "__main__":
    main()

