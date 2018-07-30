
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