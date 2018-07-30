# REST Client Library
import requests as req
# Loggers
from logging import error, warn, info
# Python3 Enumerations
from enum import Enum
# Flowmod structures
import flowmod as fm
# Collections
from collections import defaultdict
# Pretty Printer for __str__ implementations
import pprint as pp
# JSON Formatter/Serializer
import json
# Various local utility functions
import util as util

class HttpReqType(Enum):
    """
    Class: HttReqType(Enum)
    Purpose: Enumerate HTTP Request Types.
    """

    GET = 0
    POST = 1
    DELETE = 2

    def __str__(self):
        str_rep = ''
        if self == HttpReqType.GET:
            str_rep = 'GET'
        elif self == HttpReqType.POST:
            str_rep = 'POST'
        elif self == HttpReqType.DELETE:
            str_rep = 'DELETE'

class OFRequestType(Enum):
    """
    Class: OFRequestType
    Purpose: Map request types into parser implementations. 
    """

    SwitchList      = 0
    SwitchFlows     = 1
    PushFlowmod     = 2
    TopologyLinks   = 3
    SwitchDesc      = 4
    RemoveAllFlows  = 5

    @staticmethod
    def get_type_parser(req_type):
        parsers = { OFRequestType.SwitchList  : OFResponseSwitchList.parse_json 
                  , OFRequestType.SwitchFlows : OFResponseSwitchFlows.parse_json
                  , OFRequestType.PushFlowmod : OFStatusResponse.parse_json
                  , OFRequestType.TopologyLinks : OFResponseTopologyLinks.parse_json
                  , OFRequestType.SwitchDesc    : OFResponseSwitchDesc.parse_json
                  , OFRequestType.RemoveAllFlows : OFStatusResponse.parse_json
                  }
        return parsers[req_type]

    @staticmethod
    def get_http_req_type(req_type):
        http_map = { OFRequestType.SwitchList   : HttpReqType.GET
                   , OFRequestType.SwitchFlows  : HttpReqType.GET
                   , OFRequestType.PushFlowmod  : HttpReqType.POST
                   , OFRequestType.TopologyLinks : HttpReqType.GET
                   , OFRequestType.SwitchDesc : HttpReqType.GET
                   , OFRequestType.RemoveAllFlows : HttpReqType.DELETE
                   }
        return http_map[req_type]

class OFResponse:
    """
    Class: OFResponse
    Purpose: Encapsulates OpenFlow response data received via REST
    calls to the Ryu Controller.
    """

    def __init__(self):
        self.response_code = None
        pass

    @staticmethod
    def from_json(json_repr, req_type):
        if json_repr.status_code != req.codes.okay:
            raise IOError('Recieved invalid response. Error Code: %d' 
                % json_repr.status_code)
        
        parser = OFRequestType.get_type_parser(req_type)
        resp = parser(json_repr)
        return resp

    def get_response_code(self):
        return self.response_code

class OFStatusResponse(OFResponse):
    """
    Class: OFStatusResponse(OFResponse)
    Purpose: Class that will be yielded in the case of GET 
    HTTP POSTs where there is no data returned. 
    """
    
    def __init__(self):
        pass

    def parse(self, json_repr):
        self.response_code = json_repr.status_code
    
    @staticmethod
    def parse_json(json_repr):
        obj = OFStatusResponse()
        obj.parse(json_repr)
        return obj

    def __str__(self):
        str_rep = 'Status Code: %s' % str(self.response_code)
        return str_rep

        
class OFResponseSwitchList(OFResponse):
    """
    JSON Response that contains a list of switch DPIDs connected to the
    controller.
    """

    def __init__(self):
        self.switches = []

    def parse(self, json_repr):
        self.response_code = json_repr.status_code
        self.switches = json_repr.json()

    @staticmethod
    def parse_json(json_repr):
        obj = OFResponseSwitchList()
        obj.parse(json_repr)
        return obj

    def get_sw_list(self):
        """
        Return the list of switches reported by the controller.
        """
        return self.switches

    def __str__(self):
        return 'Switch DPIDs: %s' % str(self.switches)

class OFResponseSwitchFlows(OFResponse):
    """
    Class: OFResponseSwitchFlows
    Purpose: Expose information about flowmods installed on a particular 
    switch
    """

    def __init__(self):
        self.resp = None

    def parse(self, json_repr):
        self.response_code = json_repr.status_code
        self.resp = json_repr.json()

    @staticmethod
    def parse_json(json_repr):
        obj = OFResponseSwitchFlows()
        obj.parse(json_repr)
        return obj
    
    def get_flows(self):
        flow_list = []
        for sw_dpid in self.resp.values():
            flow_list = flow_list + sw_dpid
        return flow_list

    def get_flow_count(self):
        return len(self.get_flows())
    
    def __str__(self):
        str_rep = 'Flow Count: %d' % self.get_flow_count()
        return str_rep

class OFResponseTopologyLinks(OFResponse):
    """
    Class: OFResponseTopologyLinks(OFResponse)
    Purpose: Expose information about netowrk adjacency map
    """

    def __init__(self):
        self.resp = None
    
    def parse(self, json_repr):
        self.response_code = json_repr.status_code
        self.resp = json_repr.json()
    
    @staticmethod
    def parse_json(json_repr):
        obj = OFResponseTopologyLinks()
        obj.parse(json_repr)
        return obj
    
    def get_adj_mat(self):
        adj_mat = defaultdict(dict)
        for entry in self.resp:
            dst_id = entry['dst']['dpid']
            src_id = entry['src']['dpid']
            adj_mat[dst_id][src_id] = entry['dst']['port_no']
        return adj_mat

    def __str__(self):
        str_rep = pp.pformat(self.get_adj_mat())
        return str_rep

class OFResponseSwitchDesc(OFResponse):
    def __init__(self):
        self.rest = None

    def parse(self, json_repr):
        self.response_code = json_repr.status_code
        self.resp = json_repr.json()

    @staticmethod
    def parse_json(json_repr):
        obj = OFResponseSwitchDesc()
        obj.parse(json_repr)
        return obj
    
    def get_sw_dpid(self):
        dpid = None
        for k,v in self.resp.items():
            dpid = k
        return dpid

    def get_sw_name(self):
        sw_name = self.resp[self.get_sw_dpid()]['dp_desc']
        return sw_name

class OFRequest:
    """
    Class OFRequest:
    Purpose: Encapsulates OpenFlow request data to be to the controller
    via rest calls. 
    """

    def __init__(self, req_type, host, port_no):
        self.req_type = req_type
        self.host = host
        self.port_no = port_no

    def get_response(self):
        of_request = self.get_request_url()
        of_params = self.get_request_params()
        try:
            http_req_type = OFRequestType.get_http_req_type(self.req_type)
            if http_req_type == HttpReqType.GET:
                resp = req.get(of_request, data=json.dumps(of_params))
            elif http_req_type == HttpReqType.POST:
                resp = req.post(of_request, data=json.dumps(of_params))
            elif http_req_type == HttpReqType.DELETE:
                resp = req.delete(of_request, data=json.dumps(of_params))
            else:
                raise ValueError('Undefined HTTP Method')
        except req.exceptions.ConnectionError as ex:
            error(ex)
            raise e
        except Exception as ex:
            error(ex) 
            raise ex
        try:
            of_resp = OFResponse.from_json(resp, self.req_type)       
        except IOError as ex:
            error(ex)
            raise ex

        info('Successfully sent request %s.' % of_request)
        return of_resp
    
    def get_request_params(self):
        return None

    def get_host_url(self, req_str=''):
        url = 'http://%s:%d%s' % (self.host, self.port_no, req_str)
        return url

class SwitchList(OFRequest):
    """
    Class: SwitchList(OFRequest)
    Purpose: Request a list of connected switch DPIDs from the controller.
    """

    def __init__(self, host, port_no=8080):
        OFRequest.__init__(self, OFRequestType.SwitchList, host, port_no)

    def get_request_url(self):
         url = self.get_host_url('/stats/switches')
         return url

class SwitchFlows(OFRequest):
    """
    Class: SwitchFlows(OFRequest)
    Purpose: Request a list of flowmods installed on a particular switch
    """

    def __init__(self, sw_dpid, host, port_no=8080):
        OFRequest.__init__(self, OFRequestType.SwitchFlows, host, port_no)
        self.sw_dpid = sw_dpid

    def get_request_url(self):
        url = self.get_host_url('/stats/flow/%d' % self.sw_dpid)
        return url

class PushFlowmod(OFRequest):
    """
    Class: PushFlowmod(OFRequest)
    Purpose: Send a flowmod with specified parameters to a particular switch.
    """

    def __init__(self, flowmod, host, port_no=8080):
        OFRequest.__init__(self, OFRequestType.PushFlowmod, host, port_no)
        self.flowmod = flowmod

    def get_request_url(self):
        url = self.get_host_url('/stats/flowentry/add')
        return url
    
    def get_request_params(self):
        return self.flowmod.get_json()

class TopologyLinks(OFRequest):
    """
    Class: TopologyLinks(OFRequest)
    Purpose: Get the adjacency matrix for the network.
    """

    def __init__(self, host, port_no=8080):
        OFRequest.__init__(self, OFRequestType.TopologyLinks, host, port_no)
        
    def get_request_url(self):
        url = self.get_host_url('/v1.0/topology/links')
        return url

class SwitchDesc(OFRequest):
    """
    Class: SwitchDesc(OFRequest)
    Purpose: Pull information about a particular DPID from the controller.
    """

    def __init__(self, dpid, host, port_no):
        OFRequest.__init__(self, OFRequestType.SwitchDesc, host, port_no)
        self.dpid = dpid

    def get_request_url(self):
        if isinstance(self.dpid, str):
            formatted = self.dpid
        else:
            formatted = util.dpid_fmt(self.dpid)
        url = self.get_host_url('/stats/desc/%s' % formatted)
        return url

class RemoveAllFlows(OFRequest):
    """
    Class: RemoveAllFlows(OFRequest)
    Purpose: Removes all flows from the specified DPID. 
    """

    def __init__(self, dpid, host, port_no):
        OFRequest.__init__(self, OFRequestType.RemoveAllFlows, host, port_no)
        self.dpid = dpid

    def get_request_url(self):
        if isinstance(self.dpid, str):
            formatted = self.dpid
        else:
            formatted = str(self.dpid)
        url = self.get_host_url('/stats/flowentry/clear/%s' % formatted)
        return url

    