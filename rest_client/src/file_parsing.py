"""
Module: file_parsing
Purpuse: produce in-memory representations of the
input files specifying the parameters of a test.
"""
import ast
from typing import List, Dict, Tuple, Iterator

def read_node_file(path: str) -> Iterator[int]:
    """
    Method: read_node_file
    Purpose: Reads source and destination node files
    ((Destinations|Origins)_seed_[0-9]*.txt) and returns a list of integers.
    """
    node_str = ''
    with open(path, 'r') as node_file:
        node_str = node_file.read()
    node_str = node_str.replace('\r\n', '')
    node_str = node_str.replace('[', '')
    node_str = node_str.replace(']', '')
    nodes = map(int, node_str.rstrip().split('.')[0:-1])
    return nodes

def read_partitions_file(path: str) -> Dict[int, List[float]]:
    """
    Method: read_partitions_file
    Purpose: Parses the path ratios files (X_matrix_seed_[0-9]*.txt) into a
    map from flow number to List[float]
    """
    flow_dict = {}
    with open(path, 'r') as part_file:
        for line in part_file:
            str_1 = line.split(':')
            index_str = str_1[0]
            val_str = str_1[1]
            flow_num = int(index_str[2:-1].split(',')[0])
            flow_dict.setdefault(flow_num, []).append(float(val_str))
    return flow_dict

def parse_flow_defs(path: str, seed_no: str) -> Dict[Tuple[int, int], List[float]]:
    """
    Method: parse_flow_defs
    Purpose: Parse an entire flow definition. A flow definition is composed primarily
    of the path splitting ratios.
    """
    flow_dir = path
    dests = read_node_file(flow_dir + ('Destinations_seed_%s.txt') % seed_no)
    origins = read_node_file(flow_dir + ('Origins_seed_%s.txt') % seed_no)
    parts = read_partitions_file(flow_dir + ('X_matrix_seed_%s.txt') % seed_no)
    od_pairs = list(zip([O_n + 1 for O_n in origins], [D_n + 1 for D_n in dests]))
    seen = []
    for elem in od_pairs:
        if elem in seen:
            print(elem, 'is a duplicate.')
        seen.append(elem)
    flows = {}
    for ind, pair in enumerate(od_pairs):
        flows[pair] = parts[ind]
    return flows

def read_route_file(path: str) -> List[List[List[int]]]:
    """
    Method: read_route_file
    Purpose: Parse a route file and return a [[[int]]]
    """
    lst = []
    with open(path, 'r') as route_file:
        lst = ast.literal_eval(route_file.read())
    return lst

def parse_routes(path: str, seed_no: str) -> List[List[List[int]]]:
    """
    Method: parse_routes
    Purpose: Wrapper method for read_route_file that adds converts from the zero
    indexed input file to the one indexed output.
    """
    routes_path = path + 'Paths_seed_%s.txt' % seed_no
    routes = read_route_file(routes_path)
    routes = [[list(map(lambda n: n + 1, path)) for path in flow] for flow in routes]
    return routes
