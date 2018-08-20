import of_processor as ofp
import dns.resolver as dns
import dns.reversename as rev_name
import util as util

from typing import List, Union, Dict

class HostMapper:

    def __init__( self          : HostMapper
                , nameservers   : List[str]
                , host          : str
                , port_no       : int
                , domain        : str ='of.cpsc.' ) -> None:
        self.nameservers = nameservers
        self.host = host
        self.port_no = port_no
        self.domain = domain
        self.of_proc = ofp.OFProcessor(cfg.of_controller_ip, cfg.of_controller_port)

    def map_sw_to_host(self: HostMapper, sw_no: str) -> str:
        host_str = 'host%d' % int(sw_no)
        return host_str

    def resolve_hostname(self: HostMapper, hostname: str) -> Union[str, None]:
        resolver = dns.Resolver()
        resolver.nameservers = self.nameservers
        
        query_str = self.qualify_host_domain(hostname)
        try:
            answers = resolver.query(query_str, 'A')
        except dns.NXDOMAIN:
            raise IOError('Failed to resolve hostname: %s' % query_str)
        except Exception:
            raise IOError('Failed to resolve hostname: %s' % query_str)

        if answers:
            return answers[0].address
        else: 
            return None 

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
        switch_list = of_proc.get_switch_list()
        for sw in switch_list:
            resp = of_proc.get_switch_desc(sw)
            curr_no = util.sw_name_to_no(resp.get_sw_name())
            if curr_no == sw_no:
                return resp.get_sw_dpid()
        return None

    def qualify_host_domain(self: HostMapper, hostname: str) -> str:
        if hostname[-1] == '.':
            return hostname
        else:
            return ('%s.%s' % (hostname, self.domain))

    def get_switch_to_host_map(self: HostMapper) -> Dict[str, str]:
        sw_list = of_proc.get_switch_list()
        print(sw_list)
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
            
        




