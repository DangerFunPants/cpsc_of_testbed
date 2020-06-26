
import pathlib                          as path

import nw_control.results_repository    as rr
import tuiti.config                     as tuiti_config
import data_visualization.tuiti         as tuiti_graphing

def tuiti_plots():
    base_repository_path = path.Path(
        "/home/alexj/results-repositories/testing-per-path-loss-tracking")
    # results_repository = rr.ResultsRepository.create_repository(tuiti_config.base_repository_path,
    results_repository = rr.ResultsRepository.create_repository(base_repository_path,
            tuiti_config.repository_schema, tuiti_config.repository_name)

    provider_name = "tuiti-trial-provider"
    trial_provider = results_repository.read_trial_provider(provider_name)
    # tuiti_graphing.generate_link_utilization_cdf(trial_provider)
    # tuiti_graphing.generate_link_utilization_box_plot(trial_provider)
    # tuiti_graphing.generate_link_utilization_over_time_plot(trial_provider)
    tuiti_graphing.generate_per_path_packet_loss_cdf(trial_provider)
    # tuiti_graphing.generate_mean_throughput_over_time_plot(trial_provider)
    # tuiti_graphing.generate_mean_link_utilization_over_time_plot(trial_provider)

def main():
    tuiti_plots()

if __name__ == "__main__":
    main()
