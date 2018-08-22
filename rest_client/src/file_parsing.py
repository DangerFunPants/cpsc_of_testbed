
import ast
import abc
from collections import defaultdict 
import pprint as pp

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
    def __init__(self, route_dir, seed_no):
        FileParser.__init__(self)
        self._route_dir = route_dir
        self._seed_no = seed_no
    
    def _read_route_file(self, path):
        lst = []
        with open(path, 'r') as rf:
            lst = ast.literal_eval(rf.read())
        return lst

    def get_routes(self):
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
            flows.append((src, dst, parts[ind]))
        return flows

class NETestFileParser(FileParser):

    def __init__(self, route_dir, seed_no):
        self._route_dir = route_dir
        self._seed_no = seed_no

    def get_routes(self):
        routes_path = self._route_dir + './Paths_seed_%s.txt' % self._seed_no 
        with open(routes_path, 'r') as rf:
            nets = eval(rf.read())
        routes = []
        for vn_id, vn in enumerate(nets):
            for flow_id, flow in enumerate(vn):
                for path_id, path in enumerate(flow):
                    p = [ n + 1 for n in path ]
                    routes.append((path_id, p))
        return routes

    def _read_partitions_file(self, file_path):
        with open(file_path, 'r') as fd:
            lines = fd.readlines()
        flow_vs = defaultdict(lambda : defaultdict(dict))
        for line in lines:
            tup_lit = line[1:].split(':')[0]
            t = eval(tup_lit)
            flow_val = float(line.split(':')[1])
            flow_vs[t[0]][t[1]][t[2]] = flow_val
        return flow_vs

    def get_flow_defs(self):
        part_file = self._route_dir + './X_matrix_seed_%s.txt' % self._seed_no
        parts = self._read_partitions_file(part_file)
        routes = self.get_routes()
        path_splits = []
        for (net_id, net_flows) in parts.items():
            for (flow_id, paths) in net_flows.items():
                src_host = routes[0][1][0]
                dst_host = routes[0][1][-1]
                splits = list(paths.values())
                path_splits.append((src_host, dst_host, splits))
                routes.pop(0)
        return path_splits

if __name__ == '__main__':
    main()







    