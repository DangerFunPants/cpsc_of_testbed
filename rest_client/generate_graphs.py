
import pprint                                   as pp
import pathlib                                  as path

# import data_visualization.flow_mirroring        as flow_mirroring
# import data_visualization.port_mirroring        as port_mirroring
# import data_visualization.mp_routing            as mp_routing
# import data_visualization.simulations           as sim
import data_visualization.path_hopping          as path_hopping
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg
import mp_routing.params                        as mp_cfg
import simulations.params                       as sim_cfg
import path_hopping.params                      as ph_cfg   

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
    repo_path = path.Path("/home/cpsc-net-user/results-repositories/path-hopping-results")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            ph_cfg.repository_schema, ph_cfg.repository_name)
    # for trial_name in ["single-path", "path-hopping"]:
    for trial_name in ["testing-iperf"]:
        for seed_number in [12345678]:
            path_hopping.generate_link_utilization_cdf(results_repository, trial_name, seed_number)
            # path_hopping.generate_topo_utilization_graph(results_repository, trial_name)

def main():
    # flow_mirroring_plots()
    # port_mirroring_plots()
    # mp_routing_plots()
    # vle_simulation_plots()
    path_hopping_plots()

if __name__ == "__main__":
    main()
