
import pprint                                   as pp
import pathlib                                  as path

import data_visualization.link_utilization      as link_utilization
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg

def main():
    repo_path = path.Path("/home/cpsc-net-user/repos/flow-mirroring-results-4/")
    results_repository = rr.ResultsRepository.create_repository(repo_path,
            pm_cfg.repository_schema, pm_cfg.repository_name)

    link_utilization.generate_max_mirror_port_utilization_bar_plot(results_repository)
    link_utilization.generate_theoretical_vs_actual_utilization_bar_plot(results_repository)
    link_utilization.generate_approx_vs_optimal_theoretical_utilization_bar_plot(results_repository)
    link_utilization.generate_mirroring_port_utilization_bar_plot(results_repository)

    # actual, theoretical = link_utilization.compute_theoretical_and_actual_mean_utilization(results_repository)
    # pp.pprint(theoretical)

if __name__ == "__main__":
    main()
