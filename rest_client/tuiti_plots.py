
import pathlib                          as path
import itertools                        as itertools
import pprint                           as pp
import re                               as re

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

def generate_plot_groups(key_function, trial_provider):
    trials = sorted(trial_provider, key=key_function)
    for parameter_value, parameter_group in itertools.groupby(trials, key_function):
        plotter_arg_tuple = ("pname", parameter_value, list(parameter_group))
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

    # This will group trials based on whether the exact or approximate methods were used
    # approx_match = re.compile(r".*approximate.*")
    # key_function = lambda trial: approx_match.match(trial.name) != None

    # generate_plots_for_parameter("maximum-bandwidth-variation", trial_provider)

    # Group trials based on the deviation mode of the traffic.
    # key_function = lambda trial: trial.get_parameter("deviation-mode")

    # Group trials based on the deviation mode of the traffic and whether or not they 
    # are using approximate or exact methods.
    def key_function(trial):
        approx_match = re.compile(".*approximate.*")
        if approx_match.match(trial.name) == None:
            method_string = "exact"
        else:
            method_string = "approx"
        deviation_mode = trial.get_parameter("deviation-mode")
        return f"{deviation_mode}-{method_string}"

    generate_plot_groups(key_function, trial_provider)

def main():
    tuiti_plots()

if __name__ == "__main__":
    main()
