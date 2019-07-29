
import pathlib              as path
import pprint               as pp
import json                 as json
import requests             as req
import urllib.parse         as url
import time                 as time

import nw_control.params                        as cfg
import nw_control.topo_mapper                   as topo_mapper
import nw_control.host_mapper                   as host_mapper
import nw_control.host                          as host
import nw_control.stat_monitor                  as stat_monitor
import nw_control.util                          as util
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg
import port_mirroring.trial_provider            as trial_provider
import port_mirroring.trials                    as trials
import port_mirroring.onos_rest_helpers         as onos_rest_helpers
import trials.port_mirroring_trial              as port_mirroring_trial

from collections                            import namedtuple
from sys                                    import argv

def create_and_initialize_host_connections(flows):
    mapper = host_mapper.OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, 
            cfg.of_controller_port, pm_cfg.target_topo_path)
    host_ids = set()
    for flow in flows.values():
        host_ids.add(flow.path[0])
        host_ids.add(flow.path[-1])

    hosts = {}
    for host_id in host_ids:
        hostname = mapper.map_sw_to_host(host_id)
        hosts[host_id] = host.TrafficGenHost.create_host(hostname)
        hosts[host_id].connect()

    return hosts

def close_all_host_connections(hosts):
    for host in hosts.values():
        host.disconnect()

def conduct_port_mirroring_trial(provider_name, trial, results_repository):
    mapper = host_mapper.OnosMapper(cfg.dns_server_ip, cfg.of_controller_ip, 
            cfg.of_controller_port, pm_cfg.target_topo_path)

    flows           = trial.flows
    switches        = trial.switches
    solutions       = trial.solutions

    # flow_tokens = add_port_mirroring_flows(pm_cfg.target_topo_path, flows, switches, solutions)
    # flow_tokens = trial.add_flows(trial.topology, flows, switches, solutions)
    flow_tokens = trial.add_flows()

    hosts = create_and_initialize_host_connections(flows)

    destination_hosts = {flow.path[-1] for flow in flows.values()}
    for destination_host in destination_hosts:
        # @TODO: Why do I need to pass the ID to this method. Shouldn't have to 
        # tell the host about itself.
        hosts[destination_host].start_server(destination_host)

    for flow_id, flow in flows.items():
        destination_hostname    = mapper.map_sw_to_host(flow.path[-1])
        tx_rate                 = util.mbps_to_bps(flow.traffic_rate * pm_cfg.rate_factor) / 8
        tx_variance             = 0.0
        traffic_model           = "uniform"
        destination_ip          = mapper.resolve_hostname(destination_hostname)
        destination_port        = 50000
        k_mat                   = [1.0]
        host_num                = flow.path[0]
        time_slice              = 100
        pkt_len                 = 1066
        tag_value               = flow_id

        hosts[flow.path[0]].configure_client(tx_rate, tx_variance, traffic_model,
                destination_ip, destination_port, k_mat, host_num, time_slice, tag_value, pkt_len)

    traffic_monitor = stat_monitor.OnMonitor(cfg.of_controller_ip, cfg.of_controller_port)
    traffic_monitor.start_monitor()

    for source_node in {flow.path[0] for flow in flows.values()}:
        hosts[source_node].start_clients()

    time.sleep(trial.duration)

    traffic_monitor.stop_monitor()

    for host_id in {flow.path[0] for flow in flows.values()}:
        hosts[host_id].stop_client()

    # This probably isn't necessary, presumably it's to let 
    # the network "drain" before killing the server processes 
    # in order to avoid inflated loss rates.
    time.sleep(15) 

    for host_id in {flow.path[-1] for flow in flows.values()}:
        hosts[host_id].stop_server()

    close_all_host_connections(hosts)

    onos_rest_helpers.remove_port_mirroring_flows(flow_tokens)

    utilization_results = traffic_monitor.get_monitor_statistics()

    results_files = trial.build_results_files(utilization_results)

    schema_vars = { "provider-name"     : provider_name
                  , "solution-type"     : trial.solution_type
                  , "trial-name"        : trial.name
                  }
    results_repository.write_trial_results(schema_vars, results_files)

def run_provider_trials(provider):
    results_repository = rr.ResultsRepository.create_repository(pm_cfg.base_repository_path,
            pm_cfg.repository_schema, pm_cfg.repository_name)
    for trial in provider:
        conduct_port_mirroring_trial(provider.name, trial, results_repository) 

def main():
    # provider = trials.flow_mirroring_trials()
    provider = trials.port_mirroring_trials()
    # provider = trials.port_mirroring_test()
    # provider = trials.re_run_trials()
    # provider = trials.rnd_port_mirroring_trials()
    
    # for trial in provider:
    #     print(trial)
    #     # if not trial.verify_trial_state():
    #     #     print("Not all flows in trial were mirrored.")
    #     # else:
    #     #     print("All flows were mirrored successfully.")
    run_provider_trials(provider)

if __name__ == "__main__":
    main()
