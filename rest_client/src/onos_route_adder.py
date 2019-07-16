import multipath_orchestrator   as mp
import file_parsing             as fp
import params                   as cfg
import pathlib                  as path
import pprint                   as pp
import requests                 as req
import json

class OnosRouteAdder:

    def __init__(self, route_provider):
        self._route_provider = route_provider

    def install_routes(self):
        routes = self._route_provider.get_routes()
        route_count = 0
        
        for route_idx in range(0, len(routes), 3):
            self.install_route(list(routes[route_idx:route_idx+3]))
            route_count += 1
        print("Installed %d routes on physical network." % route_count)

    def install_route(self, route):
        # paths = [{path_spec[1] for path_spec in route]
        onos_credentials = ("onos", "rocks")
        paths_dicts = [{"nodes": path[1], "tagValue": path[0]} for path in route]
        route_json = json.dumps({ "paths": paths_dicts })
        print(route_json)
        route_add_request = req.post("http://127.0.0.1:8181/onos/multipath-routing/v1/add-route", data=route_json, auth=onos_credentials)
        # pp.pprint(json.loads(route_add_request.text))
        pp.pprint(route_add_request.text)
        # pp.pprint(route_json)

def build_file_path(route_files_dir, trial_name, seed_no):
    return route_files_dir.joinpath(trial_name).joinpath("seed_%s" % seed_no)

def main():
    seed_no = "4065"
    mu = cfg.mu
    sigma = cfg.sigma
    trial_path = build_file_path(path.Path(cfg.var_rate_route_path), "prob_mean_1_sigma_1.0", seed_no)
    print(str(trial_path))
    route_provider = fp.VariableRateFileParser(str(trial_path), seed_no, mu, sigma)

    route_adder = OnosRouteAdder(route_provider)

    route_adder.install_routes()

if __name__ == "__main__":
    main()
