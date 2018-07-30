import file_parsing as fp
import of_rest_client as of
import flowmod as fm
from util import *

class MPRouteAdder:
    
    def __init__( self
                , host
                , port
                , defs_dir
                , seed_no ):
        self.host = host
        self.port = port
        self.defs_dir = defs_dir
        self.seed_no = seed_no

    def get_dpid_map():
        req = of.SwitchList(self.host, self.port)
        resp = req.get_response()
        m = {}
        for i, dpid in resp.switches:
            m[i] = dpid
        return m

    def install_routes(self):
        routes = fp.parse_routes(self.defs_dir, self.seed_no)
        print(routes)
        # Get a copy of the adjacency matrix
        adj_mat = of.TopologyLinks(self.host, self.port).get_response().get_adj_mat()
        for i, route in enumerate(routes):
            for path in route:
                self.install_route(path, adj_mat, i)

    # Looking back on how this is turning out, it would have been better to inject
    # an actual instnace of some class to interact with the controller, thus indirecting
    # the consumers of that interface from its implementation. Can't really test
    # this route adding code conviniently without an actual controller and network 
    # setup.
    def install_route(self, route, adj_mat, flow_num):
        pairs = list(zip(route, route[1:]))
        print(pairs)
        for (src, dst) in pairs:
            src_dpid = dpid_fmt(src)
            dst_dpid = dpid_fmt(dst)
            print('Src: %s, Dst: %s' % (src_dpid, dst_dpid))
            out_port = adj_mat[src_dpid][dst_dpid]
            flow_mod = fm.Flowmod(src, hard_timeout=60)
            match = fm.Match(fm.MatchTypes.ipv4_src, '10.0.0.5')
            match.add_criteria(fm.MatchTypes.eth_type, 2048)
            flow_mod.add_match(match)
            flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port' : out_port}))
            req = of.PushFlowmod(flow_mod, self.host, self.port)
            resp = req.get_response()
            print(resp.response_code)
