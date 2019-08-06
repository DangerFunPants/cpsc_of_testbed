
import pprint                                   as pp
import pathlib                                  as path

import data_visualization.flow_mirroring        as flow_mirroring
import data_visualization.port_mirroring        as port_mirroring
import data_visualization.mp_routing            as mp_routing
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg

def flow_mirroring_plots():
    # results-5 : Multi provider that ran for five minutes
    repo_path = path.Path("/home/cpsc-net-user/repos/flow-mirroring-results-5/")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            "/provider-name/solution-type/trial-name/", "flow-mirroring")

    flow_mirroring.generate_max_mirror_port_utilization_bar_plot(results_repository)
    # flow_mirroring.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
    # flow_mirroring.generate_approx_vs_optimal_theoretical_utilization_bar_plot(results_repository)
    # flow_mirroring.generate_mirroring_port_utilization_bar_plot(results_repository)
    # flow_mirroring.generate_theoretical_vs_actual_compact_bar_plot(results_repository)
    # flow_mirroring.generate_mirroring_port_utilization_compact_bar_plot(results_repository)
    flow_mirroring.generate_mirroring_port_utilization_box_plot(results_repository)

def port_mirroring_plots():
    # repo_path = pm_cfg.base_repository_path
    # results-2 : Plots currently in the paper
    # results-3 : Multi provider that ran for one minute
    # results-4 : Multi provider that ran for five minutes
    repo_path = path.Path("/home/cpsc-net-user/repos/port-mirroring-results-4")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            "/provider-name/solution-type/trial-name/", "port-mirroring")

    port_mirroring.generate_max_mirror_port_utilization_bar_plot(results_repository)
    # port_mirroring.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
    # port_mirroring.generate_mirroring_port_utilization_bar_plot(results_repository)
    # port_mirroring.generate_theoretical_util_graph(results_repository)
    # port_mirroring.generate_theoretical_vs_actual_compact_bar_plot(results_repository)
    # port_mirroring.generate_port_mirroring_port_utilization_cdf(results_repository)
    # port_mirroring.generate_mirror_port_rate_difference_file(results_repository)
    # port_mirroring.generate_port_mirroring_port_utilization_compact_bar_plot(results_repository)
    port_mirroring.generate_mirroring_port_utilization_box_plot(results_repository)

def mp_routing_plots():
    mp_routing.main()

def main():
    # flow_mirroring_plots()
    # port_mirroring_plots()
    mp_routing_plots()

if __name__ == "__main__":
    main()
