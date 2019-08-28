#!/usr/bin/env python3

import socket
import signal
import os
from collections import defaultdict
import pickle
import argparse

# pkt_counts :: (src_addr, src_port) -> recv_count
byte_counts = defaultdict(int)
args = None

def get_args():
    p = argparse.ArgumentParser('Receive traffic for multipath routing experminets.')
    p.add_argument('-host', dest='host_num', metavar='<host_num>', nargs=1, 
            help='host number', required=True)
    p.add_argument("-source_addr", dest="source_addr", metavar="<source_addr>", nargs=1,
            help="Source address to bind to.", required=True)
    args = p.parse_args()
    return int(args.host_num[0]), args.source_addr[0]

def handle_sig_int(signum, frame):
    global args
    pkts_recv = { s : (bc / 1024) for s, bc in byte_counts.iteritems() }
    print(pkts_recv)
    with open("/home/alexj/packet_counts/receiver_%d.p" % args, "wb") as fd:
        pickle.dump(pkts_recv, fd)
    exit()

def inc_pkt_counts(src, bc):
    byte_counts[src] = byte_counts[src] + bc

def main():
    global args
    args, source_addr = get_args()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind((source_addr, 50000))

    while True:
        data, (addr, port_no) = sock.recvfrom(1048576)
        inc_pkt_counts((addr, port_no), len(data))

def register_handlers():
    signal.signal(signal.SIGINT, handle_sig_int)

if __name__ == '__main__':
    register_handlers()
    main()
