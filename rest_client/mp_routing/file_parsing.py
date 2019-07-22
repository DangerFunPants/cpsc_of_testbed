
import ast
import abc
import os 

import pathlib as       path
import pprint as        pp
import params as        cfg

from collections import defaultdict 

class FileParser(metaclass=abc.ABCMeta):

    def __init__(self):
        pass

    def _read_node_file(self, path): 
        node_str = ''
        with open(path, 'r') as nf:
            node_str = nf.read()
        node_str = node_str.replace('\r\n', '')
        node_str = node_str.replace('[', '')
        node_str = node_str.replace(']', '')
        nodes = map(int, node_str.rstrip().split('.')[0:-1])
        return nodes

    @abc.abstractmethod
    def get_routes(self):
        pass

    @abc.abstractmethod
    def get_flow_defs(self):
        pass

class MPTestFileParser(FileParser):
    def __init__(self, route_dir, seed_no, mu, sigma):
        FileParser.__init__(self)
        self._route_dir = route_dir
        self._seed_no = seed_no
        self._mu = mu
        self._sigma = sigma
    
    def _read_route_file(self, path):
        lst = []
        print('file_parsing -> _read_route_file: ' + str(path))
        with open(path, 'r') as rf:
            lst = ast.literal_eval(rf.read())
        print('file_parsing -> _read_route_file: ' + str(lst))
        return lst

    def get_routes(self):
        print('file_parsing -> get_routes: ' + str(self._route_dir))
        print('file_parsing -> get_routes: ' + str(self._seed_no))
        routes_path = self._route_dir + './Paths_seed_%s.txt' % self._seed_no 
        routes = self._read_route_file(routes_path)
        routes = [ (path_id, list(map(lambda n : n + 1, path))) for flow in routes for path_id, path in enumerate(flow) ]
        return routes

    def _read_partitions_file(self, path):
        flow_dict = {}
        with open(path, 'r') as pf:
            for line in pf:
                s1 = line.split(':')
                index_str = s1[0]
                val_str = s1[1]
                flow_num = int(index_str[2:-1].split(',')[0])
                flow_dict.setdefault(flow_num, []).append(float(val_str))
        return flow_dict

    def get_flow_defs(self):
        flow_dir = self._route_dir
        dests = self._read_node_file(flow_dir + ('./Destinations_seed_%s.txt') % self._seed_no)
        origins = self._read_node_file(flow_dir + ('./Origins_seed_%s.txt') % self._seed_no)
        parts = self._read_partitions_file(flow_dir + ('./X_matrix_seed_%s.txt') % self._seed_no)
        od_pairs = list(zip([O_n + 1 for O_n in origins], [D_n + 1 for D_n in dests]))
        seen = []
        for elem in od_pairs:
            if elem in seen:
                print(elem, 'is a duplicate.')
            seen.append(elem)
        flows = []
        for ind, (src, dst) in enumerate(od_pairs):
            flows.append((src, dst, parts[ind], (self._mu, self._sigma)))
        return flows

    def get_tx_rates(self):
        return {}

class NETestFileParser(FileParser):

    def __init__(self, route_dir, seed_no, mu, sigma):
        self._route_dir = route_dir
        self._seed_no = seed_no
        self._mu = mu
        self._sigma = sigma

    def get_routes(self):
        routes_path = self._route_dir.joinpath("Paths_seed_%s.txt" % self._seed_no)
        print(self._route_dir)
        print(routes_path)
        with routes_path.open("r") as rf:
            nets = eval(rf.read())
        #print('file parsing -> NETestFileParser: get_routes: nets: ' + str(nets))
        routes = []
        for vn_id, vn in enumerate(nets):
            for flow_id, flow in enumerate(vn):
                for path_id, path in enumerate(flow):
                    p = [ n + 1 for n in path ]
                    routes.append((path_id, p))
        #print('file parsing -> NETestParser: get_routes: routes: ' + str(routes))
        return routes

    def _read_partitions_file(self, file_path):
        with file_path.open("r") as fd:
            lines = fd.readlines()
        flow_vs = defaultdict(lambda : defaultdict(dict))
        for line in lines:
            tup_lit = line[1:].split(':')[0]
            t = eval(tup_lit)
            flow_val = float(line.split(':')[1])
            flow_vs[t[0]][t[1]][t[2]] = flow_val
        print('file parsing -> NETestFile Parser: _read_partiotions_file: ' + str(flow_vs))
        return flow_vs

    def get_flow_defs(self):
        part_file = self._route_dir + '/X_matrix_seed_%s.txt' % self._seed_no
        parts = self._read_partitions_file(part_file)
        routes = self.get_routes()
        path_splits = []
        for (net_id, net_flows) in parts.items():
            for (flow_id, paths) in net_flows.items():
                src_host = routes[0][1][0]
                dst_host = routes[0][1][-1]
                splits = list(paths.values())
                print((src_host, dst_host))
                path_splits.append((src_host, dst_host, splits, (self._mu, self._sigma)))
                routes = routes[3:]
        return path_splits

class VariableRateFileParser(NETestFileParser):
    def __init__(self, route_dir, seed_no, mu, sigma):
        super().__init__(route_dir, seed_no, mu, sigma)
        self._route_dir = route_dir
        self._seed_no = seed_no
        self._mu = mu
        self._sigma = sigma

    def _construct_rate_table(self):
        def get_nw_id(file_name):
            toks = file_name.split('_')
            return int(toks[2])

        def get_flow_params(line):
            toks = line.split(':')
            parm_list = toks[-1].split(',')
            mu = int(float(parm_list[0]))
            sigma = float(parm_list[1]) #int(float(parm_list[1]))
            # why? for gamma distribution, I think sigma shouldn't be zero but this problem must be handled on the hosts. 
            # Becase, we may change the distribution. 
            #sigma = sigma if sigma != 0 else 1
            return (mu, sigma)

        rate_path = self._route_dir.joinpath("rate_files/")
        # Should be one file for each VN in the trial.
        # Each of these files will contain N entries where N is the number
        # of flows in each request. Each flow contains K paths over which 
        # traffic will be forwarded. Each of these K paths should have the same
        # source and destination nodes. 
        # all_files = os.listdir(rate_path)
        all_files = [f for f in rate_path.iterdir() if f.is_file()]
        rates = defaultdict(dict)
        for nw_file in all_files:
            print(nw_file.name)
            net_id = get_nw_id(nw_file.name)
            with nw_file.open("r") as fd:
                lines = fd.readlines()
                for flow_id, line in enumerate(lines):
                    mu, sigma = get_flow_params(line)
                    rates[net_id][flow_id] = (mu * self._mu, sigma * self._sigma)
        return rates

    def get_flow_defs(self):
        part_file = self._route_dir.joinpath("X_matrix_seed_%s.txt" % self._seed_no)
        parts = self._read_partitions_file(part_file)
        routes = self.get_routes()
        path_splits = []
        tx_rates = self._construct_rate_table()
        for (net_id, net_flows) in parts.items():
            for (flow_id, paths) in net_flows.items():
                src_host = routes[0][1][0]
                dst_host = routes[0][1][-1]
                splits = list(paths.values())
                print((src_host, dst_host))
                path_splits.append((src_host, dst_host, splits, tx_rates[net_id][flow_id]))
                routes = routes[3:]
        print('file parsing -> Variable -> get_flow_defs: path_splits: ' + str(path_splits))
        return path_splits

def main():
    def build_file_path(route_files_dir, trial_name, seed_no):
        return route_files_dir.joinpath(trial_name).joinpath("seed_%s" % seed_no)

    # mapper = OnosMapper([cfg.dns_server_ip], cfg.of_controller_ip, cfg.of_controller_port)
    seed_no = "4065"
    mu = cfg.mu
    sigma = cfg.sigma
    trial_path = build_file_path(path.Path(cfg.var_rate_route_path), 
            "prob_mean_1_sigma_1.0", seed_no)
    route_provider = VariableRateFileParser(trial_path, seed_no, mu, sigma)

    routes = route_provider.get_routes()
    flow_defs = route_provider.get_flow_defs()
    pp.pprint(flow_defs)
    
if __name__ == '__main__':
    main()
    
