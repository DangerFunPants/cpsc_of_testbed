
import scipy.stats          as stats

from enum import Enum

class TrafficModels(Enum):
    UNIFORM                 = 0
    TRUNC_NORM              = 1
    RANDOM_SAMPLING         = 2
    TRUNC_NORM_SYMMETRIC    = 3
    GAMMA                   = 4
    PRECOMPUTED             = 5

    @staticmethod
    def from_str(string_rep):
        e_val = None
        string_rep = string_rep.lower()
        if string_rep == 'uniform':
            e_val = TrafficModels.UNIFORM
        elif string_rep == 'trunc_norm':
            e_val = TrafficModels.TRUNC_NORM
        elif string_rep == 'random_sampling':
            e_val = TrafficModels.RANDOM_SAMPLING
        elif string_rep == 'trunc_norm_symmetric':
            e_val = TrafficModels.TRUNC_NORM_SYMMETRIC
        elif string_rep == 'gamma':
            e_val = TrafficModels.GAMMA
        elif string_rep == "precomputed":
            e_val = TrafficModels.PRECOMPUTED
        else:
            raise ValueError('Could not parse string: %s' % string_rep)
        
        return e_val

def create_distribution(mu, sigma, traffic_model, transmit_rates):
    dist = None
    if traffic_model == TrafficModels.TRUNC_NORM or traffic_model == TrafficModels.RANDOM_SAMPLING:
        min_dist_val = 0.0
        max_dist_val = float(2**32 - 1)
        a, b = (min_dist_val - mu) / (sigma), (max_dist_val - mu) / (sigma)
        dist = stats.truncnorm(a, b, loc=mu, scale=sigma)

    elif traffic_model == TrafficModels.TRUNC_NORM_SYMMETRIC:
        min_dist_val = 0.0
        max_dist_val = mu * 2.0
        a, b = (min_dist_val - mu) / sigma, (max_dist_val - mu) / sigma
        dist = stats.truncnorm(a, b, loc=mu, scale=sigma)

    elif traffic_model == TrafficModels.UNIFORM:
        a, b = uniform_paramaters(mu, sigma)
        dist = stats.uniform(a, (b - a))

    elif traffic_model == TrafficModels.GAMMA:
        theta = (sigma / float(mu))
        dist = stats.gamma(a=(sigma / theta**2), scale=theta)

    elif traffic_model == TrafficModels.PRECOMPUTED:
        if transmit_rates == None:
            raise ValueError(
                    "Cannot use PRECOMPUTED traffic model without supplying transmit rate list.")
        rates_iter = PrecomputedTapDistribution(transmit_rates)
        dist = rates_iter

    return dist

def get_heterogeneous_link_rates(mu, sigma, number_of_samples):
    distribution = create_distribution(mu, sigma, TrafficModels.GAMMA, None)
    samples = [distribution.rvs() for _ in range(number_of_samples)]
    return samples








