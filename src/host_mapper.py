import of_rest_client as of
import dns.resolver as dns
import util as util

class HostMapper:

    def __init__(self, nameservers, host, port_no, domain='of.cpsc.'):
        self.nameservers = nameservers
        self.host = host
        self.port_no = port_no
        self.domain = domain

    def map_sw_to_host(self, sw_no):
        host_str = 'host%d' % int(sw_no)
        return host_str

    def resolve_hostname(self, hostname):
        resolver = dns.Resolver()
        answers = resolver.query(hostname, 'A')
        if answers:
            return answers[0]
        else: 
            return None 
    
    def map_dpid_to_sw(self, dpid):
        req = of.SwitchDesc(dpid, self.host, self.port_no)
        resp = req.get_response()
        return resp.get_sw_name()

    def map_sw_to_dpid(self, sw_no):
        sw_no = str(sw_no)
        switch_list = of.SwitchList(self.host, 
            self.port_no).get_response().get_sw_list()
        print(switch_list)
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
            
        




