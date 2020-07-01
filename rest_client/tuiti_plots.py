
import pathlib                          as path
import itertools                        as itertools

import nw_control.results_repository    as rr
import tuiti.config                     as tuiti_config
import data_visualization.tuiti         as tuiti_graphing

def generate_plots_for_parameter(parameter_name, trial_provider):
    parameter_selector = lambda the_trial: the_trial.get_parameter(parameter_name)
    trials = sorted(trial_provider, key=parameter_selector)
    for parameter_value, parameter_group in itertools.groupby(trials, parameter_selector):
        plotter_arg_tuple = (parameter_name, parameter_value, list(parameter_group))
        tuiti_graphing.generate_per_path_packet_loss_cdf(*plotter_arg_tuple)
        tuiti_graphing.generate_link_utilization_cdf(*plotter_arg_tuple)
        tuiti_graphing.generate_link_utilization_box_plot(*plotter_arg_tuple)
        tuiti_graphing.generate_mean_throughput_over_time_plot(*plotter_arg_tuple)
        tuiti_graphing.generate_mean_link_utilization_over_time_plot(*plotter_arg_tuple)
        tuiti_graphing.generate_number_of_successful_requests_bar_plot(*plotter_arg_tuple)

def tuiti_plots():
    base_repository_path = path.Path(
        "/home/alexj/results-repositories/testing-with-overprovisioning-and-increased-tb-size")
    # results_repository = rr.ResultsRepository.create_repository(base_repository_path,
    results_repository = rr.ResultsRepository.create_repository(tuiti_config.base_repository_path,
            tuiti_config.repository_schema, tuiti_config.repository_name)

    provider_name = "tuiti-trial-provider"
    trial_provider = results_repository.read_trial_provider(provider_name)
    # TODO: Should do this in a better way, maintain a sorted list as trials are 
    # added rather than sorting it here. 
    trial_provider._trials = sorted(trial_provider._trials)
    generate_plots_for_parameter("maximum-bandwidth-variation", trial_provider)
    # tuiti_graphing.print_tx_rate_of_sender(trial_provider)

def main():
    tuiti_plots()

if __name__ == "__main__":
    main()
