import of_rest_client as of
import flowmod as fm

from typing import Any

class OFProcessor:

    def __init__( self              : OFProcessor
                , of_controller_ip  : str
                , of_controller_port: str ) -> None:
        self._of_controller_ip = of_controller_ip
        self._of_controller_port = of_controller_port

    def _curry_of_msg_cons(self: OFProcessor, cons: Callable[Any, Any]) -> Any:
        return (lambda args : cons(*args, self._of_controller_ip, self._of_controller_port))

    def get_switch_list(self: OFProcessor) -> List[int]:
        req = self._curry_of_msg_cons(of.SwitchList)
        resp = req([]).get_response()
        return resp.get_sw_list()

    def get_switch_flows(self: OFProcessor, dpid: str) -> of.OFResposeSwitchFlows:
        req = self._curry_of_msg_cons(of.SwitchFlows)
        resp = req([dpid]).get_response()
        return resp

    def push_flow_mod( self     : OFProcessor
                     , dpid     : str
                     , flow_mod : fm.FlowMod ) -> of.OFStatusResponse:
        req = self._curry_of_msg_cons(of.PushFlowmod)
        resp = req([flow_mod]).get_response()
        return resp
    
    def get_topo_links(self: OFProcessor) -> of.OFResponseTopologyLinks:
        req = self._curry_of_msg_cons(of.TopologyLinks)
        resp = req([]).get_response()
        return resp
    
    def get_switch_desc(self: OFProcessor, dpid: str) -> of.OFResponseSwitchDesc:
        req = self._curry_of_msg_cons(of.SwitchDesc)
        resp = req([dpid]).get_response()
        return resp

    def remove_all_flows(self: OFProcessor, dpid: str) -> of.OFStatusResponse:
        req = self._curry_of_msg_cons(of.RemoveAllFlows)
        resp = req([dpid]).get_response()
        return resp

    def remove_flow( self       : OFProcessor
                   , dpid       : str
                   , flow_mod   : fm.FlowMod ) -> of.OFStatusResponse:
        req = self._curry_of_msg_cons(of.RemoveFlow)
        resp = req([dpid, flow_mod]).get_response()
        return resp

    def get_port_stats(self: OFProcessor, dpid: str) -> of.OFPortStatsResponse:
        req = self._curry_of_msg_cons(of.GetPortStats)
        resp = req([dpid]).get_response()
        return resp

    def remove_table_flows( self        : OFProcessor
                          , dpid        : str
                          , table_id    : int ) -> of.OFStatusResponse:
        flow_mod = fm.Flowmod(dpid, table_id=table_id)
        return self.remove_flow(dpid, flow_mod)

    def add_default_route( self     : OFProcessor
                         , dpid     : str
                         , table_id : int) -> of.OFStatusResponse:
        flow_mod = fm.Flowmod(dpid, priority=1, table_id=100)
        flow_mod.add_action(fm.Action(fm.ActionTypes.Output, {'port':4294967293}))
        self.push_flow_mod(dpid, flow_mod)


