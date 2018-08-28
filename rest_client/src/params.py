
"""
This file contains static configuration items that are referenced in many other
locations in the application. Ideally these would be determined via some other
means but I haven't thought of a better way to do this yet. 
"""

# DNS Server IP for OpenFlow Network
dns_server_ip = '10.0.0.2'
# DNS Server IP for management Network
man_net_dns_ip = '192.168.0.2'

# Openflow Controller address 
of_controller_ip = '10.0.1.1'
# Openflow Controller REST API Port Number
of_controller_port = 8080

# Per trial parameters
route_files = '/home/ubuntu/Downloads/corrected_routes/'
seed_no = '5678'
trial_name = lambda s : s + 'seed_' + seed_no + '/'
route_path = lambda s : route_files + trial_name(s)

# Median Tx Rate for hosts (Bps)
mu = (100000000 / 8.0)
# Sigma (variance) for hosts. (Bps)
sigma = (100000000 / 8.0) ** 2
# sigma = 1
# Traffic Model
traffic_model = 'gamma'
# Frequency of Tx Rate alteration (seconds)
time_slice = 10
# Total number of seconds to run the trial for
trial_length = 900
# Destination UDP port for test traffic
dst_port = 50000
# Data packet size (Headers included)
pkt_size = 1066
# Link Utilization sample rate
sample_freq = 10.0
