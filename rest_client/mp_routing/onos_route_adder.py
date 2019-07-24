import multipath_orchestrator   as mp
import file_parsing             as fp
import params                   as cfg
import pathlib                  as path
import pprint                   as pp
import requests                 as req
import json                     as json

from . import HostMapper
from . import OnMonitor

class OnosRouteAdder:

    def __init__( self
                , route_provider
                , mapper
                , onos_credentials = ("onos", "rocks")):
        self._route_provider            = route_provider
        self._credentials               = onos_credentials
        self._mapper                    = mapper
        self._installed_route_tokens    = set()

    def install_routes(self):
        routes = self._route_provider.get_routes()
        route_count = 0
        
        pp.pprint(routes)
        for route_idx in range(0, len(routes), 3):
            self.install_route(list(routes[route_idx:route_idx+3]))
            route_count += 1
        print("Installed %d routes on physical network." % route_count)

    def remove_route(self, route_token):
        route_remove_request = req.post("http://127.0.0.1:8181/onos/multipath-routing/v1/remove-route?route-id=%s" % route_token, auth=self._credentials)

    def remove_routes(self):
        for route_token in self._installed_route_tokens:
            self.remove_route(route_token)

    def install_route(self, route):
        # paths = [{path_spec[1] for path_spec in route]
        paths_dicts = [{"nodes": [self._mapper.map_sw_to_dpid(p_i) for p_i in path[1]], "tagValue": path[0] + 1} for path in route]
        route_json = json.dumps({ "paths": paths_dicts })
        print(route_json)
        route_add_request = req.post("http://127.0.0.1:8181/onos/multipath-routing/v1/add-route", data=route_json, auth=self._credentials)
        if route_add_request.status_code == 200:
            add_response = json.loads(route_add_request.text)
            route_token = add_response["routeId"]
            self._installed_route_tokens.add(route_token)
        else:
            raise ValueError("Failed to add route. Status code: %s. Reason: %s" % 
                    (route_add_request.status_code, route_add_request.reason))

    def get_src_dst_pairs(self):
        routes = self._route_provider.get_routes()
        pairs = set()
        for _, path in routes:
            pairs.add((path[0], path[-1]))
        return pairs

    def get_path_ratios(self):
        path_ratios = self._route_provider.get_flow_defs()
        return path_ratios

class OnosMapper(HostMapper):
    def __init__(self, dns_server_ips, controller_ip, controller_port):
        super().__init__(dns_server_ips, controller_ip, controller_port)
        self._switch_to_dpid_map = { 1  : "of:00039cdc718a17c0"
                                   , 2  : "of:00049cdc718a17c0"
                                   , 3  : "of:00039cdc718ab520"
                                   , 4  : "of:00049cdc718ab520"
                                   , 5  : "of:000400fd457cab40"
                                   , 6  : "of:00039cdc718ae5c0"
                                   , 7  : "of:00049cdc718ae5c0"
                                   , 8  : "of:000300fd457cab40"
                                   , 9  : "of:000500fd457cab40"
                                   , 10 : "of:00059cdc718ab520"
                                   , 11 : "of:00059cdc718a17c0"
                                   }
    
    def map_sw_to_dpid(self, sw_num):
        return self._switch_to_dpid_map[sw_num]

def build_file_path(route_files_dir, trial_name, seed_no):
    return route_files_dir.joinpath(trial_name).joinpath("seed_%s" % seed_no)

def main():
    seed_no = "4065"
    mu = cfg.mu
    sigma = cfg.sigma
    trial_path = build_file_path(path.Path(cfg.var_rate_route_path), "prob_mean_1_sigma_1.0", seed_no)
    print(trial_path)
    route_provider = fp.VariableRateFileParser(trial_path, seed_no, mu, sigma)

    route_adder = OnosRouteAdder(route_provider, 
            OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port))

    route_adder.install_routes()

if __name__ == "__main__":
    main()