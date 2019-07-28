
import pprint                                   as pp
import pathlib                                  as path

import data_visualization.link_utilization      as link_utilization
import data_visualization.port_mirroring        as port_mirroring
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg

def flow_mirroring_plots():
    repo_path = path.Path("/home/cpsc-net-user/repos/flow-mirroring-results-4/")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            pm_cfg.repository_schema, pm_cfg.repository_name)

    link_utilization.generate_max_mirror_port_utilization_bar_plot(results_repository)
    link_utilization.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
    link_utilization.generate_approx_vs_optimal_theoretical_utilization_bar_plot(results_repository)
    link_utilization.generate_mirroring_port_utilization_bar_plot(results_repository)

def port_mirroring_plots():
    # repo_path = pm_cfg.base_repository_path
    repo_path = path.Path("/home/cpsc-net-user/repos/port-mirroring-results-2")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            "/provider-name/solution-type/trial-name/", "port-mirroring")

    # port_mirroring.generate_max_mirror_port_utilization_bar_plot(results_repository)
    port_mirroring.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
    # port_mirroring.generate_mirroring_port_utilization_bar_plot(results_repository)
    # port_mirroring.generate_theoretical_util_graph(results_repository)

def main():
    port_mirroring_plots()

if __name__ == "__main__":
    main()
