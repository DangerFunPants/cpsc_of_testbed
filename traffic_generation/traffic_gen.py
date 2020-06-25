#!/usr/bin/env python3

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
import json                 as json
import operator             as op
import pathlib              as path

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
    REQUEST_BASED           = 6

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
        elif string_rep == "request-based":
            e_val = TrafficModels.REQUEST_BASED
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
        # UDP destination port of the flow
        self.dest_port          = dest_port
        # String representation of the flow destination IP
        self.dest_addr          = dest_addr
        # Flow splitting ratios for each of the paths
        self.prob_mat           = prob_mat
        # Transmission rate of the flow in bytes per second.
        self.tx_rate            = tx_rate
        # Variance of the flow transmission rate. This parameter is interpreted differently
        # depending on which probability distribution is being used to generate the flow
        # transmission rates.
        self.variance           = variance
        # Specifies which probability distribution to sample transmission rates from.
        self.traffic_model      = traffic_model
        # Length in bytes of each UDP packet (not? including headers)
        self.packet_len         = packet_len
        # Host ID of the flow source (i.e. the host id of this instance of the traffic generator)
        self.src_host           = src_host
        # The transmission flow rate sampling period.
        self.time_slice         = time_slice
        # The DSCP tags to use for each of the paths (i.e. if there are N paths this should be a 
        # list with N entries, where the n_{th} entry is the DSCP value to use for the n_{th} path.
        self.tag_value          = tag_value
        # List of transmission rates to use, only applicable when traffic_model is "precomputed"
        self.transmit_rates     = transmit_rates
        # The local IP address to bind to.
        self.source_addr        = source_addr
        # The payload that will be sent in each packet.
        self.data_str           = b"x" * self.packet_len

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
                  , "Tag Value: %s"         % str(self.tag_value)
                  , "Transmit Rates: %s"    % self.transmit_rates
                  , "Source Address: %s"    % self.source_addr
                  ]
        s = reduce(lambda s1, s2 : s1 + "\n" + s2, str_rep)
        return s
    
    def __repr__(self):
        return str(self)

class BulkTransferRequest:
    def __init__( self
                , request_transmit_rates
                , request_deadline
                , total_data_volume
                , dest_addr
                , dest_port
                , prob_mat
                , traffic_model
                , packet_len
                , src_host
                , time_slice
                , tag_value):
        # request_transmit_rates :: timeslot_id -> path_id -> volume of data on path in timeslot
        self.request_transmit_rates     = request_transmit_rates
        # The deadline of the request specified as a timeslot
        self.request_deadline           = request_deadline
        # The total amount of data that must be received in order to consider the request successful
        self.total_data_volume = total_data_volume
        # The destination IP Address
        self.destination_address = dest_addr
        # The destination UDP port
        self.destiation_port = dest_ort
        # The amount of traffic to send over each of the paths.
        # self.prob_mat = prob_mat
        # The length of packet to send
        self.packet_length = packet_len
        # The host id of this traffic generation instance
        self.source_host = src_host
        # The duration of the timeslice (i.e. the duration of a timeslot)
        self.time_slice_duration = time_slice
        # The DSCP tag values to use for each path.
        self.tag_values = tag_value


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
    path_to_args_file = path.Path(reduce(op.add, sys.argv[1:]))
    with path_to_args_file.open("r") as fd:
        argument_dicts = json.load(fd)

    # arg_dicts = json.loads(arg_str)
    for d in argument_dicts:
        d['traffic_model'] = TrafficModels.from_str(d['traffic_model'])

    for flow_arguments in argument_dicts:
        if flow_arguments["traffic_model"] == TrafficModels.REQUEST_BASED:
            fp_list = {i: BulkTransferRequest(**d) for i, d in enumerate(argument_dicts)}
        else:
            fp_list = {i: FlowParameters(**d) for i, d in enumerate(argument_dicts)}

    return fp_list

def inc_pkt_count(flow_num):
    global pkt_count
    pkt_count[flow_num] = pkt_count[flow_num] + 10

def compute_inter_pkt_delay(pkt_len, tx_rate, time_slice_duration):
    """
    Doesn't actually compute the inter-packet delay, computes the delay that would 
    be required to allow 10 packets to be transmitted.
    """
    if tx_rate == 0.0:
        return time_slice_duration
    return (float(pkt_len) / float(tx_rate)) * 10.0

def wait(t):
    start = time.perf_counter()
    # @TODO: It's probably fine that the traffic gen application pretty much consumes a core, but
    # it might be worth looking into making this more efficient.
    while (time.perf_counter() - start) < t:
        pass

def transmit(sock_list, ipd_list, duration, flow_params):
    # for idx, flow in enumerate(flow_params.values()):
    #     ipd_set = ipd_list[idx]
    #     for _ in range(10):
    #         sock_list[idx].sendto(flow.data_str, (flow.dest_addr, flow.dest_port))

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
                # header_for_packet = next(flow_params[i].headers)
                # headers would be a list of all the headers that need to be sent over this path in
                # this timeslot (could be from different requests, and so would have different request ids
                # in the header.
                flow[0].sendto(flow_params[i].data_str, (flow_params[i].dest_addr, flow_params[i].dest_port))
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
        the_socket.bind((source_address, 0))
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
            ipd_list.append(compute_inter_pkt_delay(fp.packet_len, r, fp.time_slice))
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

    file_path = f"/tmp/sender_{src_host_id}.p"
    with open(file_path, 'wb') as fd:
        pickle.dump(flow_info, fd)
    exit()

def register_handlers():
    signal.signal(signal.SIGINT, handle_sig_int)

def set_log_level(log_level):
    # lg.basicConfig(log_level=log_level)
    pass

# Rather than configuring flows we want to configure requests.
#   * Each request must transfer a certain amount of data per timeslot, these amounts are provided in the 
#     form of a list.
#   * The reciever needs to be able to discern data from different transfers (i.e. we need to put a header in 
#     the packet which is fine). 
#   * I think the way this currently works, transfers are already routed over the right paths so that should 
#     be fine aslong as the receiver can demux the requests.
#   * What information do we need for every request:
#       - The path_id -> timeslot_id -> volume dict (i.e. what rate to transmit at)
#       - the total bw requirement of the request. 
#       - We need to know the deadline.
#       - Deadlines are per timeslot (i.e. as long as the request is done before the timeslot specified
#         is over then the request is considered a success. So we should tag the data we send with the time
#         slot that it was sent in? This creates a big problem, we need retransmits. I don't think this is 
#         going to be all that easy. Could just not do retransmits and say that if a transfer isn't successful
#         that's fine. Doing retransmits is trick because it interferes with the scheduling in subsequent
#         timeslots.
def main():
    global flow_params
    global src_port
    flow_params = get_args()
    if flow_params[0]["traffic_model"] == TrafficModels.REQUEST_BASED:
        if  any(lambda fp: fp["traffic_model"] != TrafficModels.REQUEST_BASED, flow_params):
            exit()
        do_request_transmission(flow_params)
    else:
        if any(lambda fp: fp["traffic_model"] == TrafficModels.REQUEST_BASED, flow_params):
            exit()
        generate_traffic(flow_params)

if __name__ == '__main__':
    set_log_level(lg.INFO)
    register_handlers()
    main()
