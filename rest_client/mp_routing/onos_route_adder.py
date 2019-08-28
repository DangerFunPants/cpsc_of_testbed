import pathlib                  as path
import pprint                   as pp
import requests                 as req
import json                     as json
import urllib.parse             as url

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
        tag_counters    = defaultdict(lambda: 1)
        tag_values      = {}
        for flow_id, flow in enumerate(routes):
            self.install_route(flow_id, flow.paths, tag_values, tag_counters, flow)
        return tag_values

    def remove_route(self, route_token):
        route_remove_request = req.post(
                "http://127.0.0.1:8181/onos/multipath-routing/v1/remove-route?route-id=%s" %
                route_token, auth=self._credentials)

    def remove_routes(self):
        for route_token in self._installed_route_tokens:
            self.remove_route(route_token)

    def install_route(self, route_id, route, tag_values, tag_counters, flow):
        tag_values[route_id] = []
        paths_dicts = []
        for path in route:
            path_dict = { "nodes"       : [self._mapper.map_sw_to_dpid(p_i) for p_i in path.nodes]
                        , "tagValue"    : tag_counters[flow.source_node, flow.destination_node]
                        }
            tag_values[route_id].append(tag_counters[flow.source_node, flow.destination_node])
            tag_counters[flow.source_node, flow.destination_node] += 1
            paths_dicts.append(path_dict)

        route_json = json.dumps({ "paths": paths_dicts })
        route_add_request = req.post("http://127.0.0.1:8181/onos/multipath-routing/v1/add-route",
                data=route_json, auth=self._credentials)
        if route_add_request.status_code == 200:
            add_response = json.loads(route_add_request.text)
            route_token = add_response["routeId"]
            self._installed_route_tokens.add(route_token)
        else:
            raise ValueError("Failed to add route. Status code: %s. Reason: %s %s" % 
                    (route_add_request.status_code, route_add_request.reason))

    def get_src_dst_pairs(self):
        return {(flow.source_node, flow.destination_node)
                    for flow in self._route_provider.flows}

    def get_path_ratios(self):
        path_ratios = self._route_provider.get_flow_defs()
        return path_ratios

    def get_flows(self):
        return self._route_provider.flows

def build_file_path(route_files_dir, trial_name, seed_no):
    return route_files_dir.joinpath(trial_name).joinpath("seed_%s" % seed_no)

def install_flow(flow_json):
    request_url = url.urljoin(cfg.onos_url.geturl(), "multipath-routing/v1/add-route")
    route_add_request = req.post(request_url, json=flow_json, auth=cfg.ONOS_API_CREDENTIALS)
    if not route_add_request:
        raise ValueError("Failed to add route. %d %s %s" %
                (route_add_request.status_code, route_add_request.reason,
                    route_add_request.text))

    json_response = json.loads(route_add_request.text)
    route_token = json_response["routeId"]
    return route_token

def uninstall_flow(flow_token):
    request_url = url.urljoin(cfg.onos_url.geturl(),
            "multipath-routing/v1/remove-route?route-id=%s" % flow_token)
    route_remove_request = req.post(request_url, auth=cfg.ONOS_API_CREDENTIALS)
    if not route_remove_request:
        raise ValueError("Failed to remove route. %d %s %s" %
                (route_remove_request.status_code, route_remove_request.reason,
                    route_remove_request.text))

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
