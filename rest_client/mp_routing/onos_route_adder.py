import pathlib                  as path
import pprint                   as pp
import requests                 as req
import json                     as json

import mp_routing.multipath_orchestrator        as mp
import mp_routing.file_parsing                  as fp
import nw_control.params                        as cfg

from collections                    import defaultdict

from nw_control.host_mapper         import HostMapper
from nw_control.stat_monitor        import OnMonitor

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
        routes = self._route_provider.flows
        route_count = 0
        tag_counter     = 1
        tag_values      = {}
        for flow_id, flow in enumerate(routes):
            self.install_route(flow.paths, tag_values, tag_counter)
        return tag_values

    def remove_route(self, route_token):
        route_remove_request = req.post(
                "http://127.0.0.1:8181/onos/multipath-routing/v1/remove-route?route-id=%s" %
                route_token, auth=self._credentials)

    def remove_routes(self):
        for route_token in self._installed_route_tokens:
            self.remove_route(route_token)

    def install_route(self, route_id, route, tag_values, tag_counter):
        tag_values[route_id] = []
        for path in route:
            d = { "nodes"       : [self._mapper.map_sw_to_dpid(p_i) for p_i in path]
                , "tagValue"    : tag_counter
                }
            tag_values[route_id].append(tag_counter)
            tag_counter += 1

        route_json = json.dumps({ "paths": paths_dicts })
        print(route_json)
        route_add_request = req.post("http://127.0.0.1:8181/onos/multipath-routing/v1/add-route",
                data=route_json, auth=self._credentials)
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
