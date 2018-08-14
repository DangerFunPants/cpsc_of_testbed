#!/usr/bin/python3

import socket
import time
import random
import argparse
import os
import signal
from enum import Enum
from functools import reduce
from math import sqrt
import logging as lg
import sys as sys
from collections import defaultdict
import pprint as pp

import numpy as np
import scipy.stats as stats


class TrafficModels(Enum):
    UNIFORM = 0
    TRUNC_NORM = 1
    RANDOM_SAMPLING = 2
    TRUNC_NORM_SYMMETRIC = 3
    GAMMA = 4

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
        
        if e_val is None:
            raise ValueError('Could not parse string: %s' % string_rep)
        return e_val

class FlowParameters:
    def __init__( self
                , dest_port = 0
                , dest_addr = '0.0.0.0'
                , prob_mat = []
                , tx_rate = 131072
                , variance = 131072
                , traffic_model = TrafficModels.UNIFORM
                , packet_len = 1024
                , src_host = 0
                , time_slice = 1 
                ):
        self.dest_port = dest_port
        self.dest_addr = dest_addr
        self.prob_mat = prob_mat
        self.tx_rate = tx_rate
        self.variance = variance
        self.traffic_model = traffic_model
        self.packet_len = packet_len
        self.src_host = src_host
        self.time_slice = time_slice

    def __str__(self):
        str_rep = [ 'Dest. Port: %d' % self.dest_port
                  , 'Dest. Addr: %s' % self.dest_addr
                  , 'Prob. Mat: %s' % self.prob_mat
                  , 'Tx Rate: %d' % self.tx_rate
                  , 'Variance: %d' % self.variance
                  , 'Traffic Model: %s' % self.traffic_model
                  , 'Packet Length: %d' % self.packet_len
                  , 'Source Host: %d' % self.src_host
                  , 'Time Slice: %d' % self.time_slice
                  ]
        s = reduce(lambda s1, s2 : s1 + '\n' + s2, str_rep)
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

# Considers the list of flows to be zero indexed and takes into account
# that test flows use DSCP values in the range [1, 2**6)
def calc_dscp_val(flow_num):
    return (flow_num + 1) << 2

def create_distribution(mu, sigma, traffic_model):
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
        
    return dist

def uniform_paramaters(mu, sigma2):
    b = (sqrt(12 * sigma2) + 2 * mu) / 2.0
    a = 2 * mu - b
    return (a, b)

def sample_distr(distr):
    return distr.rvs()

def select_tx_rate(args, old_rate, distr):
    tx_rate = 0
    if args.traffic_model is TrafficModels.UNIFORM:
        tx_rate = sample_distr(distr)
    elif args.traffic_model is TrafficModels.TRUNC_NORM:
        tx_rate = sample_distr(distr)
    elif args.traffic_model is TrafficModels.RANDOM_SAMPLING:
        if random.choice([0,1]) == 0:
            tx_rate = sample_distr(distr)
        else:
            tx_rate = old_rate
    elif args.traffic_model is TrafficModels.TRUNC_NORM_SYMMETRIC:
        tx_rate = sample_distr(distr)
    elif args.traffic_model is TrafficModels.GAMMA:
        tx_rate = sample_distr(distr)
    return (tx_rate)

# Takes a one dimensional matrix of length k as an argument and returns
# the DSCP value that a packet should be tagged with. 
#
# The i_th entry of <prob_matrix> contains the proportion of the flow 
# (udp stream) that should be sent over path i, thus the constraint: 
#
#       \sigma_i=0^k{prob_matrix_i} = 1
#
# should hold for all instances of prob_matrix
def select_dscp(prob_matrix):
    random_pick = random.uniform(0, 1)
    accumulator = 0.0

    for flow_num, proportion in enumerate(prob_matrix):
        accumulator = accumulator + proportion
        if (random_pick <= accumulator):
            return calc_dscp_val(flow_num)

def set_dscp(sock, dscp):
    sock.setsockopt(socket.SOL_IP, socket.IP_TOS, dscp)

def build_arg_parser():
    p = argparse.ArgumentParser('Generate traffic for multipath routing experminets.')
    p.add_argument('-p', dest='dest_port', metavar='<port_num>', nargs=1, help='dest. port number', required=True)
    p.add_argument('-a', dest='dest_ip', metavar='<ip_addr>', nargs=1, help='dest. IP address', required=True)
    p.add_argument('-k', dest='prob', metavar='<probability_matrix', nargs='+', help='path probabilities')
    p.add_argument('-t', dest='throughput', metavar='<throughput>', nargs=1, help='Mean Tx Rate',)
    p.add_argument('-s', dest='variance', metavar='<variance>', nargs=1, help='Tx Rate Variance')
    p.add_argument('-c', dest='constant', metavar='<traffic_model>', nargs=1, help='[ uniform | trunc_norm | random_sampling ]')
    p.add_argument('-host', dest='src_host', metavar='<src_host>', nargs=1, help='src_host', required=True)
    p.add_argument('-slice', dest='time_slice', metavar='<slice_len>', nargs=1, help='distribution sampling rate')
    p.add_argument('-n', dest='flow_count', metavar='<flow_count>', nargs=1, help='Number of flows')
    return p

def build_flow_params(args):
    dest_port = int(args.dest_port[0])
    dest_addr = args.dest_ip[0]
    prob_mat = []
    if args.prob is not None:
        prob_mat = list(map(float, args.prob))
    if args.throughput is not None:
        tx_rate = int(args.throughput[0])
    if args.variance is not None:
        variance = int(args.variance[0])
    if args.constant is not None:
        traffic_model = TrafficModels.from_str(args.constant[0])
    if args.time_slice is not None:
        time_slice = int(args.time_slice[0])
    src_host = int(args.src_host[0])
        
    flow_params = FlowParameters( dest_port=dest_port
                                , dest_addr=dest_addr
                                , prob_mat=prob_mat
                                , tx_rate=tx_rate
                                , variance=variance
                                , traffic_model=traffic_model
                                , src_host=src_host
                                , time_slice=time_slice
                                )
    return flow_params

def get_args():
    arg_str = sys.argv[1]
    arg_dicts = eval(arg_str)
    for d in arg_dicts:
        d['traffic_model'] = TrafficModels.from_str(d['traffic_model'])
    fp_list = { i: FlowParameters(**d) for i, d in enumerate(arg_dicts) }
    return fp_list

def inc_pkt_count(flow_num):
    global pkt_count
    pkt_count[flow_num] = pkt_count[flow_num] + 1

def compute_inter_pkt_delay(pkt_len, tx_rate):
    return (float(pkt_len) / float(tx_rate))

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
            dscp_val = select_dscp(flow_params[i].prob_mat)
            set_dscp(flow[0], dscp_val)
            flow[0].sendto(DATA_STR, (flow_params[i].dest_addr, flow_params[i].dest_port))
            inc_pkt_count(i)
            ipds[i] = (ipds[i][0], ipd_list[i])
        t_offset = max(0.0, time.perf_counter() - loop_start)
        wait_time = min(ipds.values(), key=lambda t : t[1])[1] - t_offset
        wait(wait_time)
        actual_wait = time.perf_counter() - loop_start
        ipds = { i: (s, t - actual_wait) for i, (s, t) in ipds.items() }

def generate_traffic(flow_params):
    socks = { i: socket.socket(type=socket.SOCK_DGRAM) for i in flow_params.keys() }
    rvs = { i: create_distribution(fp.tx_rate, fp.variance, fp.traffic_model) for i, fp in flow_params.items() }
    while True:
        ipd_list = []
        for i, fp in flow_params.items():
            r = select_tx_rate(fp, fp.tx_rate, rvs[i])
            mbps = (r * 8) / float(10**6)
            print('TX: %s' % str(mbps))
            ipd_list.append(compute_inter_pkt_delay(fp.packet_len, r))
        transmit(socks, ipd_list, flow_params[0].time_slice, flow_params)

def handle_sig_int(signum, frame):
    for flow_num, fp in flow_params.items():
        file_path = ('/home/alexj/packet_counts/sender_%s-%s.txt' 
            % (fp.src_host, fp.dest_addr.split('.')[-1]))
        with open(file_path, 'w') as fd:
            fd.write('%d\n' % pkt_count[flow_num])
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
