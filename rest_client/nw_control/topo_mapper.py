import urllib.parse         as url
import networkx             as nx
import requests             as req
import json                 as json

import nw_control.params            as cfg
import port_mirroring.params        as pm_cfg

def build_graph_from_topo_file(topo_file):
    text = topo_file.read_text()
    return build_graph_from_topo_string(text)

def build_graph_from_topo_string(topo_str):
    lines = topo_str.splitlines()
    graph = nx.Graph()
    num_nodes = int(lines[0])
    for node_idx in range(1, num_nodes + 1):
        graph.add_node(node_idx)
    
    for edge_entry in lines[2:]:
        [source_node, destination_node] = edge_entry.split(" ")
        graph.add_edge(int(source_node), int(destination_node))

    return graph

def generate_graph_isomorphism(g1, g2):
    graph_matcher = nx.algorithms.isomorphism.GraphMatcher(g1, g2)
    if not graph_matcher.is_isomorphic():
        raise ValueError("Trying to generate isomorphism for non-isomorphic graphs")
    return graph_matcher.mapping

def get_collector_switch_dpid():
    # request_url = url.urljoin(cfg.onos_url.geturl(), "v1/hosts")
    # hosts_request = req.get(request_url, auth=cfg.ONOS_API_CREDENTIALS)
    # if hosts_request.status_code != 200:
    #     raise ValueError("Failed to get hosts from ONOS controller. Stats %d %s." %
    #             (hosts_request.status_code, hosts_request.reason))
    # hosts = json.loads(hosts_request.text)["hosts"]
    hosts = get_nw_hosts()
    collector_host = next(host for host in hosts if cfg.collector_host_ip in host["ipAddresses"])
    return collector_host["locations"][0]["elementId"]

def get_nw_links():
    request_url = url.urljoin(cfg.onos_url.geturl(), "v1/links")
    links_request = req.get(request_url, auth=cfg.ONOS_API_CREDENTIALS)
    if links_request.status_code != 200:
        raise ValueError("Failed to get links from ONOS controller. Status %d %s." %
                (links_request.status_code, links_request.reason))
    links = json.loads(links_request.text)
    return links["links"]

def get_nw_hosts():
    requests_url = url.urljoin(cfg.onos_url.geturl(), "v1/hosts")
    hosts_request = req.get(requests_url, auth=cfg.ONOS_API_CREDENTIALS)
    if hosts_request.status_code != 200:
        raise ValueError("Failed to get hosts from ONOS controller. Status %d %s." %
                (links_request.status_code, links_request.reason))
    hosts = json.loads(hosts_request.text)
    return hosts["hosts"]

def build_onos_topo_graph():
    links = get_nw_links()
    graph = nx.Graph()
    node_set = set()
    collector_switch_dpid = get_collector_switch_dpid()
    core_topo_links = [link for link in links if link["src"]["device"] != collector_switch_dpid 
            and link["dst"]["device"] != collector_switch_dpid]

    for link in core_topo_links:
        source_dpid = link["src"]["device"]
        destination_dpid = link["dst"]["device"]
        
        if source_dpid not in node_set and source_dpid:
            node_set.add(source_dpid)
            graph.add_node(source_dpid)
        if destination_dpid not in node_set:
            node_set.add(destination_dpid)
            graph.add_node(destination_dpid)
        graph.add_edge(source_dpid, destination_dpid)
    return graph

def get_ports_that_connect(source_dpid, destination_dpid):
    links = get_nw_links()
    for link in links:
        if link["src"]["device"] == source_dpid and link["dst"]["device"] == destination_dpid:
            return (int(link["src"]["port"]), int(link["dst"]["port"]))
    raise ValueError("Could not find link connecting %s and %s" % (source_dpid, destination_dpid))

def get_host_port(switch_dpid):
    hosts = get_nw_hosts()
    for host in hosts:
        host_locations = host["locations"]
        for host_location in host_locations:
            if (host_location["elementId"] == switch_dpid and 
                    pm_cfg.collector_ip_addr not in host["ipAddresses"] and
                    cfg.dns_server_ip not in host["ipAddresses"]):
                return int(host_location["port"])
    raise ValueError("Could not find host connected to switch with DPID %s" %
            switch_dpid)

def get_and_validate_onos_topo(target_topo_string):
    def find_where_graphs_differ(target_graph, actual_graph):
        target_adj_list = target_graph.adj
        actual_adj_list = actual_graph.adj
        for actual_entry, target_entry in zip(actual_adj_list.items(), target_adj_list.items()):
            if actual_entry != target_entry:
                print("Expected node %s to have edges to %s links. Found edges to %s" %
                        (actual_entry[0], target_entry[1].keys(), actual_entry[1].keys()))

    current_topo = build_onos_topo_graph()
    target_topo = build_graph_from_topo_string(target_topo_string)
    try:
        dpid_to_id = generate_graph_isomorphism(current_topo, target_topo)
    except ValueError as ex:
        print("Failed to find isomorphism between current ONOS topology and target topology.")
        find_where_graphs_differ(target_topo, current_topo)
        raise ex
        
    id_to_dpid = {v: k for k, v in dpid_to_id.items()}
    return id_to_dpid

def verify_flows_against_nw_topo(target_topo_file, flows):
    nw_graph = build_onos_topo_graph()
    id_to_dpid = get_and_validate_onos_topo(target_topo_file.read_text())
    invalid_edges = set()
    for flow_id, flow in flows.items():
        flow_path = flow.path
        print("%s" % str(flow))
        for u, v in zip(flow_path, flow_path[1:]):
            if not nw_graph.has_edge(id_to_dpid[u], id_to_dpid[v]):
                print("\tNetwork graph does not contain edge between %d and %d (%s -> %s)" %
                        (u, v, id_to_dpid[u], id_to_dpid[v]))
                invalid_edges.add((u, v))
    return invalid_edges

def verify_flows_against_target_topo(target_topo_file, flows):
    target_graph = build_graph_from_topo_file(target_topo_file)
    id_to_dpid = get_and_validate_onos_topo(target_topo_file.read_text())
    invalid_edges = set()
    for flow_id, flow in flows.items():
        flow_path = flow.path
        print(str(flow))
        for u, v in zip(flow_path, flow_path[1:]):
            if not target_graph.has_edge(u, v):
                print("\tNetwork graph does not contain edge between %d and %d (%s -> %s)" %
                        (u, v, id_to_dpid[u], id_to_dpid[v]))
                invalid_edges.add((u, v))
    return invalid_edges

def get_switch_mirroring_ports():
    requests_url = url.urljoin(cfg.onos_url.geturl(), "port-mirroring/v1/mirroring-ports")
    mirroring_ports_request = req.get(requests_url, auth=cfg.ONOS_API_CREDENTIALS)
    if mirroring_ports_request.status_code != 200:
        raise ValueError(
                "Failed to get switch mirroring ports from ONOS controller. Status %d %s." % 
                (mirroring_ports_request.status_code, mirroring_ports_request.reason))
    mirroring_ports = json.loads(mirroring_ports_request.text)
    return json.loads(mirroring_ports["result"])
