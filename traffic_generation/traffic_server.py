#!/usr/bin/env python3

import pprint           as pp
import socket           as socket
import signal           as signal
import os               as os
import pickle           as pickle
import argparse         as argparse

from collections        import defaultdict

# pkt_counts :: (src_addr, src_port) -> recv_count
byte_counts = defaultdict(int)
# request_statistics = (request_id, timeslot_id, source_port, source_address) -> byte_count
request_statistics = defaultdict(int)
args = None

def get_args():
    p = argparse.ArgumentParser('Receive traffic for multipath routing experminets.')
    p.add_argument('-host', dest='host_num', metavar='<host_num>', nargs=1, 
            help='host number', required=True)
    p.add_argument("-source_addr", dest="source_addr", metavar="<source_addr>", nargs=1,
            help="Source address to bind to.", required=True)
    p.add_argument("--mode", dest="mode", metavar="<mode>", nargs=1,
            help="Request | Flow", required=True)
    args = p.parse_args()
    return int(args.host_num[0]), args.source_addr[0], args.mode[0]

def handle_sig_int(signum, frame):
    global args
    packets_received = { s : bc for s, bc in byte_counts.items() }
    # Should decide on a better IPC mechanism than just named files since
    # the communication becomes dependent on the structure of the host filesystem.
    # The IPC mechanism should ideally work across machine boundaries as well as on 
    # the same machine.
    with open("/tmp/receiver_%d.p" % args, "wb") as fd:
        pickle.dump(packets_received, fd)
    print(dict(request_statistics))
    exit()

def inc_pkt_counts(src, bc):
    # byte_counts[src] = byte_counts[src] + bc
    byte_counts[src] += 1

def parse_packet_data(packet_buffer):
    request_id = packet_buffer[0] | (packet_buffer[1] << 8)
    timeslot_id = packet_buffer[2] | (packet_buffer[3] << 8)
    return (request_id, timeslot_id)

def receive_data_for_requests(receiver_socket):
    while True:
        data, (source_address, port_number) = receiver_socket.recvfrom(1048576)
        request_id, timeslot_id = parse_packet_data(data)
        record_packet_reception(request_id, timeslot_id, port_number, source_address, len(data))

def record_packet_reception(request_id, timeslot_id, port_number, source_address, payload_length):
    global request_statistics
    request_statistics[request_id, timeslot_id, port_number, source_address] += 1


def receive_data_for_flows(receiver_socket):
    while True:
        data, (addr, port_no) = receiver_socket.recvfrom(1048576)
        inc_pkt_counts((addr, port_no), len(data))
    
def main():
    global args
    args, source_addr, operation_mode = get_args()
    receiver_socket = socket.socket(type=socket.SOCK_DGRAM)
    receiver_socket.bind((source_addr, 50000))

    if operation_mode.lower() == "request":
        receive_data_for_requests(receiver_socket)
    elif operation_mode.lower() == "flow":
        receive_data_for_flows(receiver_socket)

def register_handlers():
    signal.signal(signal.SIGINT, handle_sig_int)

if __name__ == '__main__':
    register_handlers()
    main()
