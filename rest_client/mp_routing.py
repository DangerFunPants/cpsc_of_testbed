
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
import mp_routing.trial                 as trial
import nw_control.stat_monitor          as stat_monitor

from collections        import defaultdict

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

def conduct_onos_trial(route_adder, trial_length):
    # remove_all_count_files(route_adder)
    mapper = host_mapper.OnosMapper(cfg.dns_server_ip, cfg.of_controller_ip, 
            cfg.of_controller_port, ABILENE_TOPO_FILE_PATH.read_text())

    hosts = create_and_initialize_host_connections(route_adder, mapper)
    for host_id, host in hosts.items():
        host.start_server()
    
    time.sleep(5)

    tag_values = route_adder.install_routes()
    path_ratios = route_adder.get_path_ratios()
    for flow_id, (src_host, dst_host, path_split, (mu, sigma)) in enumerate(path_ratios):
        dst_hostname    = mapper.map_sw_to_host(dst_host)
        dst_ip          = mapper.resolve_hostname(dst_hostname)
        # mu              = (float(mu) / 8) * 10**6
        # sigma           = (sigma / 8) * 10**6
        mu              = 10**6 / 8
        sigma           = 0
        hosts[src_host].configure_client(mu, sigma, mp_cfg.traffic_model,
                dst_ip, mp_cfg.dst_port, path_split, src_host, mp_cfg.time_slice,
                tag_values[flow_id])

    od_pairs = route_adder.get_src_dst_pairs()
    for source_node in set((s for (s, _) in od_pairs)):
        hosts[source_node].start_clients()

    traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
    traffic_monitor.start_monitor()

    # time.sleep(trial_length)
    input("Press enter to continue...")
    traffic_monitor.stop_monitor()

    for source_node in set((s for (s, _) in od_pairs)):
        hosts[source_node].stop_client()

    # time.sleep(15)

    for host_id in hosts:
        hosts[host_id].stop_server()

    utilization_results = traffic_monitor.get_monitor_statistics()
    utilization_results_out_path = path.Path("./utilization-results.txt")
    utilization_results_out_path.write_text(json.dumps(utilization_results))

    route_adder.remove_routes()

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

    trial_path = path.Path("./test-trial.json")
    trial_json = json.loads(trial_path.read_text())
    the_trial = trial.Trial.from_json(trial_json)
    route_provider = the_trial
    route_adder = onos.OnosRouteAdder(route_provider, mapper)
    try:
        conduct_onos_trial(route_adder, 60)
    except Exception as ex:
        print("Failed to conduct onos_trial")
        print(ex)
        route_adder.remove_routes()
        raise ex

if __name__ == "__main__":
    main()
