
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
route_files = '/home/ubuntu/cpsc_of_tb/route_files/'
seed_no = 'simple'
trial_name = 'seed_' + seed_no + '/'
route_path = route_files + trial_name

# Median Tx Rate for hosts (Bps)
mu = (2 * 13107200)
# Sigma (variance) for hosts. (Bps)
sigma = 1
# Traffic Model
traffic_model = 'gamma'
# Frequency of Tx Rate alteration (seconds)
time_slice = 10
# Total number of seconds to run the trial for
trial_length = 120
# Destination UDP port for test traffic
dst_port = 50000
# Data packet size (Headers included)
pkt_size = 1066
# Link Utilization sample rate
sample_freq = 10.0


