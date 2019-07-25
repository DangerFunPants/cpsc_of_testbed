
import data_visualization.link_utilization      as link_utilization
import nw_control.results_repository            as rr
import port_mirroring.params                    as pm_cfg

def main():
    results_repository = rr.ResultsRepository.create_repository(pm_cfg.base_repository_path,
            pm_cfg.repository_schema, pm_cfg.repository_name)

    link_utilization.generate_max_mirror_port_utilization_bar_plot(results_repository)

if __name__ == "__main__":
    main()
