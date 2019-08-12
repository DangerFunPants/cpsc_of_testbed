
import pathlib      as path
import pprint       as pp
import numpy        as np
import math         as math

SUMMARY_FILE_PATH = path.Path("/home/cpsc-net-user/repos/cpsc_of_testbed/rest_client/traffic_analysis/summary-files/")

# Now that we have these traces there are a few things that need to be done
#   1. Modify the traffic generation tool so that it will transmit at rates derived from the
#      traces
#   2. Modify the executor application to pass the correct set of rates to the traffic
#      generator instances running on the end hosts.
#
#
# Modifying the traffic generator:
#   * Implement a new distribution type called "precomputed" or something along those
#     lines
#   * Using this distribution type implies that the caller supplies an extra command line
#     parameter that has a list of transmit rates. The application will begin by transmitting
#     at the rate at the 0th index of the list. The application will progress through the list,
#     incrimenting its "rate index" with some specified period.

class PrecomputedTapDistribution:
    def __init__(self, rates_list):
        self._rates_list    = rates_list
        self._rate_idx      = 0

    def __next__(self):
        rate_to_return = self._rates_list[self._rate_idx]
        self._rate_idx = (self._rate_idx + 1) % len(self._rates_list)
        return rate_to_return

    def __iter__(self):
        return self

def parse_traffic_summary(traffic_summary_str):
    summary_entries = []
    for line in traffic_summary_str.splitlines():
        summary_entries.append(eval(line))
    return summary_entries

def load_traffic_summary_from_file(file_path):
    traffic_summary_str = file_path.read_text()
    return parse_traffic_summary(traffic_summary_str)

def scale_traffic_rates(summary):
    return [[r_i*16/10**8 for r_i in s_i] for s_i in summary]

def get_rate_list():
    file_path   = SUMMARY_FILE_PATH / path.Path("nyc19_sec")
    summary     = load_traffic_summary_from_file(file_path)
    summary     = scale_traffic_rates(summary)
    std_dev     = [np.std(s_i) for s_i in summary]
    means       = [np.mean(s_i) for s_i in summary]
    return summary[0]

def get_rates_for_flows():
    file_path   = SUMMARY_FILE_PATH / path.Path("nyc19_sec")
    summary     = load_traffic_summary_from_file(file_path)
    summary     = scale_traffic_rates(summary)
    std_dev     = [np.std(s_i) for s_i in summary]
    means       = [np.mean(s_i) for s_i in summary]
    return summary, means, std_dev

def get_95th_percentile_rates_for_flows():
    summary, means, std_dev = get_rates_for_flows()
    percentile_mean_rates = []
    for rate_list in [sorted(r_i) for r_i in summary]:
        percentile_index = math.ceil(0.95 * len(rate_list))
        percentile_mean_rates.append(rate_list[percentile_index])
    return summary, percentile_mean_rates, std_dev

def main():
    r = get_rate_list()
    print(np.mean(r))

if __name__ == "__main__":
    main()











