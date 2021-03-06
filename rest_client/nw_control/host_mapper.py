import pprint               as pp

import dns.resolver         as dns
import dns.reversename      as rev_name

from . import util

from . import of_rest_client    as of
from . import topo_mapper       as topo_mapper

class HostMapper:
    def __init__(self, nameservers, host, port_no, domain='data.sdn.'):
        self.nameservers = nameservers
        self.host = host
        self.port_no = port_no
        self.domain = domain

    def map_sw_to_host(self, sw_no):
        host_str = 'host%d' % int(sw_no)
        return host_str

    def resolve_hostname(self, hostname):
        resolver = dns.Resolver()
        resolver.nameservers = self.nameservers
        
        query_str = self.qualify_host_domain(hostname)
        try:
            answers = resolver.query(query_str, 'A')
        except Exception as ex:
            raise IOError('Failed to resolve hostname: %s. Exception: %s' % 
                    (query_str, str(ex)))

        if answers:
            return answers[0].address
        else: 
            return None 

    def get_ip_address_for_host_number(self, host_number):
        hostname = self.map_sw_to_host(host_number)
        return self.resolve_hostname(hostname)
    
    def reverse_lookup(self, ip_addr):
        dns_resolver = dns.Resolver()
        dns_resolver.nameservers = self.nameservers
        name = rev_name.dns.reversename.from_address(ip_addr)
        try:
            answers = dns_resolver.query(name, 'PTR')
        except dns.NXDOMAIN:
            raise IOError('Failed to resolve IP: %s' % name)
        except Exception:
            raise IOError('Failed to resolve IP: %s' % name)
        if answers:
            return str(answers[0])
        else:
            return None

    def map_dpid_to_sw(self, dpid):
        req = of.SwitchDesc(dpid, self.host, self.port_no)
        resp = req.get_response()
        return resp.get_sw_name()

    def map_dpid_to_sw_num(self, dpid):
        sw_name = self.map_dpid_to_sw(dpid)
        num = sw_name.split('_')[1]
        return int(num)

    def map_sw_to_dpid(self, sw_no):
        sw_no = str(sw_no)
        switch_list = of.SwitchList(self.host, 
            self.port_no).get_response().get_sw_list()
        for sw in switch_list:
            req = of.SwitchDesc(str(sw), self.host, self.port_no)
            resp = req.get_response()
            curr_no = util.sw_name_to_no(resp.get_sw_name())
            if curr_no == sw_no:
                return resp.get_sw_dpid()
        return None

    def qualify_host_domain(self, hostname):
        if hostname[-1] == '.':
            return hostname
        else:
            return ('%s.%s' % (hostname, self.domain))

    def get_switch_to_host_map(self):
        req = of.SwitchList(self.host, self.port_no)
        sw_list = req.get_response().get_sw_list()
        res = {}
        for sw_dpid in sw_list:
            # Find the friendly switch name
            dec_dpid = str(sw_dpid)
            sw_name = self.map_dpid_to_sw(dec_dpid)
            # Now find the corresponsding host name
            sw_num = sw_name.split('_')[-1]
            host_name = self.map_sw_to_host(sw_num)
            # Now lookup the IP of the host
            fqdn = self.qualify_host_domain(host_name)
            host_ip = self.resolve_hostname(fqdn)
            res[sw_dpid] = host_ip
        return res

class OnosMapper(HostMapper):
    def __init__(self, dns_server_ip, controller_ip, controller_port, target_topo_file):
        super().__init__([dns_server_ip], controller_ip, controller_port)
        self._switch_to_dpid_map = topo_mapper.get_and_validate_onos_topo(target_topo_file)

    def map_sw_to_dpid(self, sw_num):
        return self._switch_to_dpid_map[sw_num]

class MininetHostMapper:
    """
    In the case that we're using Mininet we need a way of knowing what IP address to put in the
    destination field of the IP header. There is no DNS server running on the network so
    whatever application that is responsible for generating traffic will not be able to resolve
    hostnames that way.

    Instead we just ask the ONOS controller to tell us the IPs of all the hosts that it knows
    about which lets as easily resolve host IPs.
    """
    def __init__(self):
        self._connected_hosts = topo_mapper.get_nw_hosts()

    def find_host(self, switch_dpid):
        try:
            return next((host for host in self._connected_hosts 
                if host["locations"][0]["elementId"] == switch_dpid
                and len(host["ipAddresses"]) > 0
                and "10.123.123.1" not in host["ipAddresses"]))
        except StopIteration:
            raise ValueError(f"Could not find host attached to switch with DPID {switch_dpid}")

    def get_ip_of_connected_host(self, switch_dpid):
        attached_host = self.find_host(switch_dpid)
        return attached_host["ipAddresses"][0]

    # TODO: This will break in many obvious and trivial scenarios but for mininet it should work
    # since we can control IP allocation.
    def resolve_hostname(self, hostname):
        return f"10.0.0.{int(hostname[1:])+1}"
