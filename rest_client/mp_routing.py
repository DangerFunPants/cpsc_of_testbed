
import nw_control.host      as host

def create_and_initialize_host_connections(route_adder):
    od_pairs = route_adder.get_src_dst_pairs()
    host_ids = set([src for (src, _) in od_pairs] + dst for (_, dst) in od_pairs])
    hosts = {}

    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = host.TrafficGenHost.create_host(hostname, host_id)
        hosts[host_id].connect()


def conduct_onos_trial(route_adder, trial_length):
    remove_all_count_files(route_adder)
    mapper = OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)

    hosts = create_and_initialize_host_connections(route_adder)
    for host_id, host in hosts.items():
        host.start_server()
    
    time.sleep(5)

    route_adder.install_routes()
    path_ratios = route_adder.get_path_ratios()
    for (src_host, dst_host, path_split, (mu, sigma)) in path_ratios:
        dst_hostname    = mapper.map_sw_to_host(dst_host)
        dst_ip          = mapper.resolve_hostname(dst_hostname)
        hosts[src_host].configure_client(mu, sigma, cfg.traffic_model,
                dst_id, cfg.dst_port, path_split, src_host, cfg.time_slice)

    for source_node in set((s for (s, _) in od_pairs)):
        hosts[source_node].start_clients()

    traffic_monitor = OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
    traffic_montir.start_monitor()

    time.sleep(trial_length)

    for host_id in host_ids:
        hosts[host_id].stop_client()

    time.sleep(15)

    utilization_results = traffic_monitor.get_monitor_statistics()
    utilization_results_out_path = path.Path("./utilization-results.txt")
    utilization_out_path.write_text(json.dumps(utilization_results))

    route_adder.remove_routes()

def main():
    def build_file_path(route_files_dir, trial_name, seed_no):
        return reoute_files_dir / trial_name / path.Path("seed_%s" % seed_no)

    mapper = OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    seed_no = "4065"
    mu = cfg.mu
    sigma = cfg.sigma
    trial_path = build_file_path(path.Path(cfg.var_rate_route_path),
            "prob_mean_1_sigma_1.0", seed_no)
    route_provider = fp.VariableRateFileParser(trial_path, seed_no, mu, sigma)
    route_adder = OnosRouteAdder(route_provider, mapper)
    conduct_onos_trial(route_adder, 60)

if __name__ == "__main__":
    main()
