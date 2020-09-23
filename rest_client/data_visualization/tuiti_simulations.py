import pathlib as path
import numpy as np
import data_visualization.helpers as helpers
from math import sqrt




# algorithm_fs_names = ["avg_app", "avg_k_app", "eb_k_app_90", "eb_k_app_95", "eb_k_app_99", "ts_dev_app"]
algorithm_fs_names = ["avg_k_app", "eb_k_app_90", "eb_k_app_95", "eb_k_app_99", "ts_dev_app"]
algorithm_display_names = ["xAVG K", "xEB90", "xEB95", "xEB99", "xBESD"]

P = 10  # Number of paths
T = 50  # Number of time-slots
# R = 20  # Number of flows
TS = 180  # seconds
MV = 40  # Maximum variation of BW over time
ARRI = 4
DUR = 10
DEM = 10
DEV_VAL = 7
DEV = "TS"


def build_file_path( plot_kind
                   , deviation_mode
                   , deviation_value
                   , path_count
                   , arrival
                   , duration
                   , demand
                   , variation):
    file_name = f"{plot_kind}_{deviation_mode}-{deviation_value}_P-{path_count}_ARRI-{arrival}_DUR-{duration}_DEM-{demand}_MV-{variation}"
    return file_name

def read_data_points(file_path):
    return [float(line) for line in file_path.read_text().splitlines()]

def compute_error_value(data_points):
    mean = np.mean(data_points)
    util = sum((p_i - mean)**2 for p_i in data_points)
    count2 = len(data_points)
    if count2 == 1:
        sn_util = 0
    else:
        sn_util = sqrt(util/count2)

    beta_util = 1.96 * sn_util / sqrt(count2)
    return beta_util

def generate_number_of_paths_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_vals = []
        for dev_value, x_value in zip(dev_values, x_values):
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, dev_value, x_value, ARRI, DUR, DEM, MV)
            data_points = read_data_points(file_name) 
            # mean_acc_rate = np.mean(data_points)
            mean_acc_rate = sum(data_points) / len(data_points)
            error_val = compute_error_value(data_points)
            scatter_ys.append(mean_acc_rate)
            error_vals.append(error_val)
        return scatter_ys, error_vals
    
    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [1, 2, 5, 10, 15]
    dev_values = [1, 2, 4, 7, 11]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-paths.pdf", "profit-paths.pdf", "success-rate-paths.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]

    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.xticks([i for i in range(1, 16)], [i for i in range(1, 16)])
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"No. of Paths")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)

def generate_mean_demand_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_values = []
        for x_value in x_values:
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, DEV_VAL, P, ARRI, DUR, x_value, MV)
            data_points = read_data_points(file_name) 
            mean_acc_rate = np.mean(data_points)
            error_value = compute_error_value(data_points)
            scatter_ys.append(mean_acc_rate)
            error_values.append(error_value)
        return scatter_ys, error_values

    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [2, 12, 40, 80, 100]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-demand.pdf", "profit-demand.pdf", "success-rate-demand.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]

    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"Mean demand of requests (ts)")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)

def generate_number_of_requests_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_values = []
        for x_value in x_values:
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, DEV_VAL, P, x_value, DUR, DEM, MV)
            data_points = read_data_points(file_name)
            mean_value = np.mean(data_points)
            error_value = compute_error_value(data_points)
            scatter_ys.append(mean_value)
            error_values.append(error_value)
        return scatter_ys, error_values

    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [1, 3, 5, 7, 9]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-arrival.pdf", "profit-arrival.pdf", "success-rate-arrival.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]
    
    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"Request arrival rate ($\lambda$)")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)

def generate_mean_duration_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_values = []
        for x_value in x_values:
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, DEV_VAL, P, ARRI, x_value, DEM, MV)
            data_points = read_data_points(file_name)
            mean_value = np.mean(data_points)
            error_value = compute_error_value(data_points)
            scatter_ys.append(mean_value)
            error_values.append(error_value)
        return scatter_ys, error_values

    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [10, 12, 14, 16, 18]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-duration.pdf", "profit-duration.pdf", "success-rate-duration.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]

    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"Mean duration of requests (ts)")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)

def generate_variation_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_values = []
        for x_value in x_values:
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, DEV_VAL, P, ARRI, DUR, DEM, x_value)
            data_points = read_data_points(file_name)
            mean_value = np.mean(data_points)
            error_value = compute_error_value(data_points)
            scatter_ys.append(mean_value)
            error_values.append(error_value)
        return scatter_ys, error_values

    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [30, 40]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-mv.pdf", "profit-mv.pdf", "success-rate-mv.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]

    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"Max deviation from mean (\%)")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)

def generate_ts_plots(root_sim_data_directory):
    def generate_data_for_type(results_directory, plot_kind):
        scatter_ys = []
        error_values = []
        for x_value in x_values:
            file_name = results_directory / \
                    build_file_path(plot_kind, DEV, x_value, P, ARRI, DUR, DEM, MV)
            data_points = read_data_points(file_name)
            mean_value = np.mean(data_points)
            error_value = compute_error_value(data_points)
            scatter_ys.append(mean_value)
            error_values.append(error_value)
        return scatter_ys, error_values

    results_folder = root_sim_data_directory / "non-fixed" / "TS"
    x_values = [7, 8, 9, 10]
    y_labels = [r"Acceptance Rate (\%)", r"Total Profit", r"Success Rate (\%)"]
    plot_names = ["acc-rate-ts.pdf", "profit-ts.pdf", "success-rate-ts.pdf"]
    plot_kinds = ["acc_rate", "prof", "success_rate"]

    for kind_idx, plot_kind in enumerate(plot_kinds):
        for plot_idx, algorithm in enumerate(algorithm_fs_names):
            scatter_ys, error_values = generate_data_for_type(results_folder / algorithm, plot_kind)
            helpers.plot_a_scatter(x_values, scatter_ys, idx=plot_idx, label=algorithm_display_names[plot_idx],
                    err=error_values)
        helpers.ylabel(y_labels[kind_idx])
        helpers.xlabel(r"Gamma$_{1}$(t)")
        helpers.save_figure(plot_names[kind_idx], num_cols=3)


def main():
    root_dir = path.Path("/home/alexj/sim-results/")
    generate_number_of_paths_plots(root_dir)
    # generate_mean_demand_plots(root_dir)
    # generate_number_of_requests_plots(root_dir)
    # generate_mean_duration_plots(root_dir)
    # generate_variation_plots(root_dir)
    # generate_ts_plots(root_dir)

if __name__ == "__main__":
    main()
