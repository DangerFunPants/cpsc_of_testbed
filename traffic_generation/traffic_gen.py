#!/usr/bin/python3

import socket               as socket                   
import time                 as time
import random               as random
import argparse             as argparse
import os                   as os
import signal               as signal
import logging              as lg
import sys                  as sys
import pprint               as pp
import pickle               as pickle
import scipy.stats          as stats

from enum               import Enum
from functools          import reduce
from math               import sqrt
from collections        import defaultdict

class PrecomputedTapDistribution:
    def __init__(self, rates_list):
        self._rates_list    = rates_list
        self._rate_idx      = 0

    def __next__(self):
        rate_to_return = self._rates_list[self._rate_idx]
        self._rate_idx = (self._rate_idx + 1) % len(self._rates_list)
        return rate_to_return

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

class FlowParameters:
    def __init__( self
                , dest_port         = 0
                , dest_addr         = "0.0.0.0"
                , prob_mat          = []
                , tx_rate           = 131072
                , variance          = 131072
                , traffic_model     = TrafficModels.UNIFORM
                , packet_len        = 1024
                , src_host          = 0
                , time_slice        = 1 
                , tag_value         = None
                , transmit_rates    = None
                , source_addr       = None
                ):
        self.dest_port          = dest_port
        self.dest_addr          = dest_addr
        self.prob_mat           = prob_mat
        self.tx_rate            = tx_rate
        self.variance           = variance
        self.traffic_model      = traffic_model
        self.packet_len         = packet_len
        self.src_host           = src_host
        self.time_slice         = time_slice
        self.tag_value          = tag_value
        self.transmit_rates     = transmit_rates
        self.source_addr        = source_addr

    def __str__(self):
        str_rep = [ "Dest. Port: %d"        % self.dest_port
                  , "Dest. Addr: %s"        % self.dest_addr
                  , "Prob. Mat: %s"         % self.prob_mat
                  , "Tx Rate: %d"           % self.tx_rate
                  , "Variance: %d"          % self.variance
                  , "Traffic Model: %s"     % self.traffic_model
                  , "Packet Length: %d"     % self.packet_len
                  , "Source Host: %d"       % self.src_host
                  , "Time Slice: %d"        % self.time_slice
                  , "Tag Value: %d"         % self.tag_value
                  , "Transmit Rates: %s"    % self.transmit_rates
                  , "Source Address: %s"    % self.source_addr
                  ]
        s = reduce(lambda s1, s2 : s1 + "\n" + s2, str_rep)
        return s
    
    def __repr__(self):
        return str(self)

# Default UDP payload length in bytes. 
DEF_PCKT_LEN = 1024

# Test data
DATA_STR = b'x' * DEF_PCKT_LEN

# Define the sampling rate for Tx rate selection: 
#           F_s = 1 / SLICE_DURATION.
SLICE_DURATION = 1

pkt_count = defaultdict(int)
flow_params = None
sock_dict = None

# Considers the list of flows to be zero indexed and takes into account
# that test flows use DSCP values in the range [1, 2**6)
def calc_dscp_val(flow_num, tag_values):
    return (tag_values[flow_num]) << 2

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

def uniform_paramaters(mu, sigma2):
    b = (sqrt(12 * sigma2) + 2 * mu) / 2.0
    a = 2 * mu - b
    return (a, b)

def sample_distr(distr):
    return distr.rvs()

def select_tx_rate(args, old_rate, distr):
    tx_rate = 0
    if args.traffic_model == TrafficModels.UNIFORM:
        tx_rate = sample_distr(distr)
    elif args.traffic_model == TrafficModels.TRUNC_NORM:
        tx_rate = sample_distr(distr)
    elif args.traffic_model == TrafficModels.RANDOM_SAMPLING:
        if random.choice([0,1]) == 0:
            tx_rate = sample_distr(distr)
        else:
            tx_rate = old_rate
    elif args.traffic_model == TrafficModels.TRUNC_NORM_SYMMETRIC:
        tx_rate = sample_distr(distr)
    elif args.traffic_model == TrafficModels.GAMMA:
        tx_rate = sample_distr(distr)
    elif args.traffic_model == TrafficModels.PRECOMPUTED:
        tx_rate = next(distr)

    return tx_rate

# Takes a one dimensional matrix of length k as an argument and returns
# the DSCP value that a packet should be tagged with. 
#
# The i_th entry of <prob_matrix> contains the proportion of the flow 
# (udp stream) that should be sent over path i, thus the constraint: 
#
#       \sigma_i=0^k{prob_matrix_i} = 1
#
# should hold for all instances of prob_matrix
def select_dscp(prob_matrix, tag_values):
    random_pick = random.uniform(0, 1)
    accumulator = 0.0

    for flow_num, proportion in enumerate(prob_matrix):
        accumulator = accumulator + proportion
        if (random_pick <= accumulator):
            return calc_dscp_val(flow_num, tag_values)

def set_dscp(sock, dscp):
    sock.setsockopt(socket.SOL_IP, socket.IP_TOS, dscp)

def get_args():
    arg_str = sys.argv[1]
    arg_dicts = eval(arg_str)
    for d in arg_dicts:
        d['traffic_model'] = TrafficModels.from_str(d['traffic_model'])
    fp_list = { i: FlowParameters(**d) for i, d in enumerate(arg_dicts) }
    return fp_list

def inc_pkt_count(flow_num):
    global pkt_count
    pkt_count[flow_num] = pkt_count[flow_num] + 10

def compute_inter_pkt_delay(pkt_len, tx_rate):
    return (float(pkt_len) / float(tx_rate)) * 10.0

def wait(t):
    start = time.perf_counter()
    while (time.perf_counter() - start) < t:
        pass

def transmit(sock_list, ipd_list, duration, flow_params):
    ipds = { i : (sock_list[i], ipd_list[i]) for i in range(len(ipd_list)) }
    start_time = time.time()
    wait_time = min(ipds.values(), key=lambda t : t[1])
    while (time.time() - start_time) < duration:
        loop_start = time.perf_counter()
        expired = [ i for i, (_, t) in ipds.items() if t <= 0.0 ]
        for i in expired:
            flow = ipds[i]

            for _ in range(10):
                dscp_val = select_dscp(flow_params[i].prob_mat, flow_params[i].tag_value)
                set_dscp(flow[0], dscp_val)
                flow[0].sendto(DATA_STR, (flow_params[i].dest_addr, flow_params[i].dest_port))
            inc_pkt_count(i)
            ipds[i] = (ipds[i][0], ipd_list[i])
        t_offset = max(0.0, time.perf_counter() - loop_start)
        wait_time = min(ipds.values(), key=lambda t : t[1])[1] - t_offset
        wait(wait_time)
        actual_wait = time.perf_counter() - loop_start
        ipds = { i: (s, t - actual_wait) for i, (s, t) in ipds.items() }

def create_socket(source_address):
    the_socket = socket.socket(type=socket.SOCK_DGRAM)
    if source_address:
        the_socket.bind(source_address)
    return the_socket

def generate_traffic(flow_params):

    socks = {i: create_socket(flow_params[i].source_addr) for i in flow_params.keys()}
    global sock_dict
    sock_dict = socks
    rvs = {i: create_distribution(fp.tx_rate, fp.variance, fp.traffic_model, fp.transmit_rates) 
            for i, fp in flow_params.items()}
    while True:
        ipd_list = []
        for i, fp in flow_params.items():
            r = select_tx_rate(fp, fp.tx_rate, rvs[i])
            mbps = (r * 8) / float(10**6)
            print('TX: %s' % str(mbps))
            ipd_list.append(compute_inter_pkt_delay(fp.packet_len, r))
        transmit(socks, ipd_list, flow_params[0].time_slice, flow_params)

def handle_sig_int(signum, frame):
    flow_info = defaultdict(dict)
    src_host_id = None
    for flow_num, fp in flow_params.items():
        flow_info[flow_num]['pkt_count'] = pkt_count[flow_num]
        flow_info[flow_num]['src_port'] = sock_dict[flow_num].getsockname()[1]
        flow_info[flow_num]['src_host'] = fp.src_host
        flow_info[flow_num]['dst_ip'] = fp.dest_addr
        src_host_id = fp.src_host # TODO: Store canonical src_host id

    file_path = '/home/alexj/packet_counts/sender_%d.p' % src_host_id
    with open(file_path, 'wb') as fd:
        pickle.dump(flow_info, fd)
    exit()

def register_handlers():
    signal.signal(signal.SIGINT, handle_sig_int)

def set_log_level(log_level):
    # lg.basicConfig(log_level=log_level)
    pass

def main():
    global flow_params
    global src_port
    flow_params = get_args()
    
    print('ARGS:\n%s' % pp.pformat(str(flow_params)))
    generate_traffic(flow_params)

if __name__ == '__main__':
    set_log_level(lg.INFO)
    register_handlers()
    main()
