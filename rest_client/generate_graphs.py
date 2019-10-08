
import pprint                                   as pp
import pathlib                                  as path

# import data_visualization.flow_mirroring        as flow_mirroring
# import data_visualization.port_mirroring        as port_mirroring
# import data_visualization.mp_routing            as mp_routing
# import data_visualization.simulations           as sim
import data_visualization.path_hopping              as path_hopping
import data_visualization.security                  as security
import data_visualization.mininet_benchmarks        as mininet_benchmarks
import data_visualization.path_hopping_attacker     as path_hopping_attacker
import data_visualization.path_hopping_simulations  as path_hopping_sim
import nw_control.results_repository                as rr
import port_mirroring.params                        as pm_cfg
import mp_routing.params                            as mp_cfg
import simulations.params                           as sim_cfg
import path_hopping.params                          as ph_cfg   

# def flow_mirroring_plots():
#     # results-5 : Multi provider that ran for five minutes
#     repo_path = path.Path("/home/cpsc-net-user/repos/flow-mirroring-results-5/")
#     results_repository = rr.ResultsRepository.create_repository(repo_path,
#             "/provider-name/solution-type/trial-name/", "flow-mirroring")
# 
#     flow_mirroring.generate_max_mirror_port_utilization_bar_plot(results_repository)
#     # flow_mirroring.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
#     # flow_mirroring.generate_approx_vs_optimal_theoretical_utilization_bar_plot(results_repository)
#     # flow_mirroring.generate_mirroring_port_utilization_bar_plot(results_repository)
#     # flow_mirroring.generate_theoretical_vs_actual_compact_bar_plot(results_repository)
#     # flow_mirroring.generate_mirroring_port_utilization_compact_bar_plot(results_repository)
#     flow_mirroring.generate_mirroring_port_utilization_box_plot(results_repository)
# 
# def port_mirroring_plots():
#     # repo_path = pm_cfg.base_repository_path
#     # results-2 : Plots currently in the paper
#     # results-3 : Multi provider that ran for one minute
#     # results-4 : Multi provider that ran for five minutes
#     repo_path = path.Path("/home/cpsc-net-user/repos/port-mirroring-results-4")
#     results_repository = rr.ResultsRepository.create_repository(repo_path,
#             "/provider-name/solution-type/trial-name/", "port-mirroring")
# 
#     port_mirroring.generate_max_mirror_port_utilization_bar_plot(results_repository)
#     # port_mirroring.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
#     # port_mirroring.generate_mirroring_port_utilization_bar_plot(results_repository)
#     # port_mirroring.generate_theoretical_util_graph(results_repository)
#     # port_mirroring.generate_theoretical_vs_actual_compact_bar_plot(results_repository)
#     # port_mirroring.generate_port_mirroring_port_utilization_cdf(results_repository)
#     # port_mirroring.generate_mirror_port_rate_difference_file(results_repository)
#     # port_mirroring.generate_port_mirroring_port_utilization_compact_bar_plot(results_repository)
#     port_mirroring.generate_mirroring_port_utilization_box_plot(results_repository)
# 
# def mp_routing_plots():
#     repo_path = path.Path("/home/cpsc-net-user/repos/mp-routing-results-2/")
#     # trial_type = "link-embedding"
#     trial_type = "link-embedding"
#     trial_name = "test-trial-830656277" 
#     # trial_name = "test-trial"
#     results_repository = rr.ResultsRepository.create_repository(repo_path,
#             "/trial-type/trial-name/", mp_cfg.repository_name)
#             # mp_cfg.repository_schema, mp_cfg.repository_name)
# 
#     throughput_file = path.Path("/home/cpsc-net-user/repos/tnsm-cap-file-analysis/graphing/throughput.txt")
#     path_data_file = path.Path("/home/cpsc-net-user/repos/tnsm-cap-file-analysis/graphing/path-data.txt")
# 
#     # mp_routing.generate_link_utilization_bar_plot(results_repository, trial_type, trial_name)
#     # mp_routing.generate_loss_rates(results_repository, trial_type, trial_name)
#     # mp_routing.expected_link_utilization(results_repository, trial_type, trial_name)
#     # mp_routing.generate_link_utilization_box_plot(results_repository) 
#     # mp_routing.generate_flow_rate_plot(results_repository)
#     # mp_routing.generate_flow_means_plot()
#     # mp_routing.generate_loss_rate_cdf(results_repository)
#     # mp_routing.generate_topo_utilization_graph(results_repository, trial_type, trial_name)
#     # mp_routing.generate_throughput_over_time_plot(throughput_file)
#     # mp_routing.generate_traffic_on_path_bar_plot(path_data_file)
#     # mp_routing.generate_virtual_link_count_plot(results_repository)
#     mp_routing.generate_heterogeneous_links_instantaneous_rate_plot()
#     # mp_routing.print_mean_and_standard_deviation_of_trace_rates()
#     mp_routing.generate_heterogeneous_links_mean_rate_plot()
# 
# def vle_simulation_plots():
#     repo_path = path.Path("/home/cpsc-net-user/repos/simulation-results-4/")
#     results_repository = rr.ResultsRepository.create_repository(repo_path,
#             sim_cfg.repository_schema, sim_cfg.repository_name)
#     sim.generate_simulation_run_time_plot(results_repository)

def path_hopping_plots():
    repo_path = path.Path("/home/cpsc-net-user/results-repositories/path-hopping-trial-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    # for provider_name in ["varying-k-values", "single-path-routing"]:
    for provider_name in ["optimal-varying-k"]:
        path_hopping.generate_link_utilization_cdf(results_repository, provider_name)
        # path_hopping.generate_link_utilization_box_plot(results_repository, provider_name)
        path_hopping.generate_expected_link_utilization_cdf(results_repository, provider_name)
        # path_hopping.generate_topo_utilization_graph(results_repository, provider_name)

def path_hopping_multiflow_plots(trial_provider):
    path_hopping.generate_computed_link_utilization_cdf(trial_provider) 
    path_hopping.generate_flow_count_bar_plot(trial_provider)
    path_hopping.generate_node_probability_histogram(trial_provider)
    # path_hopping.generate_substrate_topology_graph(results_repository)
    path_hopping.generate_computed_link_utilization_box_plot(trial_provider)

def generate_path_hopping_plots_for_multiple_providers():
    provider_names = [ "multiflow-tests-binomial"
                     , "multiflow-tests-uniform"
                     ]

    repo_path = path.Path("/home/cpsc-net-user/results-repositories/multiflow-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    for provider_name in provider_names:
        trial_provider = results_repository.read_trial_provider(provider_name)
        pre_process_trial_data(trial_provider)
        path_hopping_multiflow_plots(trial_provider)

def security_plots():
    security.generate_all_plots()

def mininet_benchmark_plots():
    mininet_benchmarks.generate_all_plots()

def test_plot():
    repo_path = path.Path("/home/cpsc-net-user/results-repositories/multiflow-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    trial_provider = results_repository.read_trial_provider("multiflow-tests-binomial")
    path_hopping.generate_measured_link_utilization_cdf(trial_provider)

def pre_process_trial_data(trial_provider):
    for t_i in trial_provider:
        if t_i.has_parameter("measured-link-utilization"):
            link_utilization = t_i.get_parameter("measured-link-utilization")
            for link_id in link_utilization.keys():
                link_utilization[link_id] = min(link_utilization[link_id], 20.0) / 20.0
            # t_i.update_parameter("measured-link-utilization", link_utilization) 
            # pp.pprint(t_i.get_parameter("measured-link-utilization"))

def testbed_multiflow_plots():
    repo_path = path.Path("/home/cpsc-net-user/results-repositories/multiflow-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    trial_provider = results_repository.read_trial_provider("multiflow-tests-uniform")
    pre_process_trial_data(trial_provider)
    path_hopping.generate_computed_link_utilization_cdf(trial_provider)

def print_statistics():
    repo_path = path.Path("/home/cpsc-net-user/results-repositories/multiflow-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    trial_provider = results_repository.read_trial_provider("multiflow-tests-binomial")
    pre_process_trial_data(trial_provider)
    path_hopping.print_admitted_flow_statistics(trial_provider)

def attacker_plots():
    results_repository = rr.ResultsRepository.create_repository(ph_cfg.base_repository_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    # provider_name = "delta-values"
    provider_name = "k-values"
    trial_provider = results_repository.read_trial_provider(provider_name)
    computed_trial_provider = results_repository.read_trial_provider(provider_name + "-computed")
    # path_hopping_attacker.display_statistics_for_fixed_attacker(trial_provider)
    # path_hopping_attacker.display_statistics_for_random_attacker(trial_provider)
    # path_hopping_attacker.display_capture_statistics(trial_provider)
    # path_hopping_attacker.display_statistics_for_synchronized_random_attacker(trial_provider)
    # path_hopping_attacker.generate_data_recovery_data(trial_provider, "timestep")
    path_hopping_attacker.generate_data_recovery_versus_k_scatter(computed_trial_provider)
    # path_hopping_attacker.generate_data_recovery_versus_delta_scatter(computed_trial_provider)

def simulation_plots():
    results_repository = rr.ResultsRepository.create_repository(
        path.Path("/home/cpsc-net-user/results-repositories/path-hopping-simulations"),
        ph_cfg.repository_schema, "path-hopping-simulations")
    trial_provider = results_repository.read_trial_provider("sim-path-length")
    path_hopping_sim.generate_data_recovery_vs_param_plot(trial_provider, "path-length")


def main():
    # flow_mirroring_plots()
    # port_mirroring_plots()
    # mp_routing_plots()
    # vle_simulation_plots()
    # generate_path_hopping_plots_for_multiple_providers()
    # security_plots()
    # mininet_benchmark_plots()
    # test_plot()
    # testbed_multiflow_plots()
    # print_statistics()
    attacker_plots()
    # simulation_plots()

if __name__ == "__main__":
    main()
