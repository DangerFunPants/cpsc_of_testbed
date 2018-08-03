import of_rest_client as of


class OFProcessor:

    def __init__(self, of_controller_ip, of_controller_port):
        self._of_controller_ip = of_controller_ip
        self._of_controller_port = of_controller_port

    def _curry_of_msg_cons(self, cons):
        return (lambda args : cons(*args, self._of_controller_ip, self._of_controller_port))

    def get_switch_list(self):
        req = self._curry_of_msg_cons(of.SwitchList)
        resp = req([]).get_response()
        return resp.get_sw_list()

    def get_switch_flows(self, dpid):
        req = self._curry_of_msg_cons(of.SwitchFlows)
        resp = req([dpid]).get_response()
        return resp

    def push_flow_mod(self, dpid, flow_mod):
        req = self._curry_of_msg_cons(of.PushFlowmod)
        resp = req([dpid, flow_mod]).get_response()
        return resp
    
    def get_topo_links(self):
        req = self._curry_of_msg_cons(of.TopologyLinks)
        resp = req([]).get_response()
        return resp
    
    def get_switch_desc(self, dpid):
        req = self._curry_of_msg_cons(of.SwitchDesc)
        resp = req([dpid]).get_response()
        return resp

    def remove_all_flows(self, dpid):
        req = self._curry_of_msg_cons(of.RemoveAllFlows)
        resp = req([dpid]).get_response()
        return resp

    def remove_flow(self, dpid, flow_mod):
        req = self._curry_of_msg_cons(of.RemoveFlow)
        resp = req([dpid, flow_mod]).get_response()
        return rest

    def get_port_stats(self, dpid):
        req = self._curry_of_msg_cons(of.GetPortStats)
        resp = req([dpid]).get_response()
        return resp

