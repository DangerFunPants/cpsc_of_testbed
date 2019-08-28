
"""
This file contains static configuration items that are referenced in many other
locations in the application. Ideally these would be determined via some other
means but I haven't thought of a better way to do this yet. 
"""

import urllib.parse as url

# DNS Server IP for OpenFlow Network
dns_server_ip = '10.0.0.1'

# Openflow Controller address 
of_controller_ip = '10.0.0.3'

# Openflow Controller REST API Port Number
of_controller_port = 8181

# Base URL for ONOS rest calls
onos_url = url.urlparse("http://%s:%d/onos/" % (of_controller_ip, of_controller_port))

# IP Address of the collector host (for port mirroring)
collector_host_ip = "10.10.0.18"

# Credentials for the ONOS REST API.
ONOS_API_CREDENTIALS = ("onos", "rocks")

# See dns_server_ip
man_net_dns_ip = dns_server_ip
