from enum import Enum
from functools import (reduce)
from util import set_field
from typing import List, Dict, Any

class IPProto(Enum):
    ICMP    = 2
    TCP     = 6
    UDP     = 17

class Flowmod:
    """
    Class: Flowmod
    Purpose: Programmatic representation of OpenFlow Flow modification 
    messages. 
    """

    def __init__( self                  : Flowmod
                , dpid                  : int
                , cookie                : int = None
                , cookie_mask           : int = None
                , table_id              : int = None       
                , idle_timeout          : int = None
                , hard_timeout          : int = None
                , priority              : int = None
                , flags                 : int = None
                ) -> None:
        self.dpid = dpid
        self.cookie = cookie
        self.cookie_mask = cookie_mask
        self.table_id = table_id
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.priority = priority
        self.flags = flags

        self.match = {}
        self.actions = []

    def add_match(self: Flowmod, match: Match) -> None:
        for k, v in match.get_match_params().items():
            self.match[k] = v
    
    def add_action(self: Flowmod, action: Action) -> None:
        action_rep = action.get_dict()
        self.actions = self.actions + [action_rep]

    def get_json(self: Flowmod) -> Dict[str, Any]:
        json_dict = {}
        json_dict['dpid'] = self.dpid
        json_dict = set_field(json_dict, 'dpid', self.dpid)
        json_dict = set_field(json_dict, 'cookie', self.cookie)
        json_dict = set_field(json_dict, 'cookie_mask', self.cookie_mask)
        json_dict = set_field(json_dict, 'table_id', self.table_id)
        json_dict = set_field(json_dict, 'idle_timeout', self.idle_timeout)
        json_dict = set_field(json_dict, 'hard_timeout', self.hard_timeout)
        json_dict = set_field(json_dict, 'priority', self.priority)
        json_dict = set_field(json_dict, 'flags', self.flags)

        json_dict['match'] = self.match
        json_dict['actions'] = self.actions
        return json_dict

    def __str__(self: Flowmod) -> str:
        str_rep = ('Switch: %s, Flow Table: %s\n' 
            % (str(self.dpid), str(self.table_id)))
        str_rep += 'Match Criteria: \n'
        for k, v in self.match.items():
            str_rep += '\t%s: %s\n' % (k, v)
        str_rep += 'Actions: \n'
        for i, act in enumerate(self.actions):
            str_rep += '\taction %d\n' % i
            s = map(lambda p : '\t\t'+p+'\n', str(act).split('\n'))
            s = reduce(lambda s1, s2: s1+s2, s)
            str_rep += s
            
        return str_rep

class MatchTypes(Enum):
    """
    Class: MatchTypes
    Purpose: Enumerate the various field in a packet header that OpenFlow 1.3
    implementations are capable of matching on.
    """

    in_port     = 0     # Int
    eth_dst     = 1     # String of the form '01:23:45:67:89:ab'
    eth_src     = 2     # String of the form '01:23:45:67:89:ab' 
    eth_type    = 3     # Int
    vlan_vid    = 4     # Int or String
    vlan_pcp    = 5     # Int
    ip_dscp     = 6     # Int (lower 6 bits only)
    ip_ecn      = 7     # Int (lower 2 bits only)
    ip_proto    = 8     # Int
    ipv4_src    = 9     # String of the form '192.168.0.1'
    ipv4_dst    = 10    # String of the form '192.168.0.1'
    tcp_src     = 11    # Int
    tcp_dst     = 12    # Int
    udp_src     = 13    # Int
    udp_dst     = 14    # Int
    icmpv4_code = 15    # Int
    icmpv4_type = 16    # Int
    arp_op      = 17    # Int
    arp_spa     = 18    # String of the form '192.168.0.1'
    arp_tpa     = 19    # String of the form '192.168.0.1
    arp_sha     = 20    # String of the form '01:23:45:67:89:ab'
    arp_tha     = 21    # String of the form '01:23:45:67:89:ab'

    @staticmethod
    def to_string(match_type: MatchTypes) -> str:
        d = {}
        d[MatchTypes.in_port]     = 'in_port'
        d[MatchTypes.eth_dst]     = 'eth_dst'
        d[MatchTypes.eth_src]     = 'eth_src'
        d[MatchTypes.eth_type]    = 'eth_type'
        d[MatchTypes.vlan_vid]    = 'vlan_vid'
        d[MatchTypes.vlan_pcp]    = 'vlan_pcp'
        d[MatchTypes.ip_dscp]     = 'ip_dscp'
        d[MatchTypes.ip_ecn]      = 'ip_ecn'
        d[MatchTypes.ip_proto]    = 'ip_proto'
        d[MatchTypes.ipv4_src]    = 'ipv4_src'
        d[MatchTypes.ipv4_dst]    = 'ipv4_dst'
        d[MatchTypes.tcp_src]     = 'tcp_src'
        d[MatchTypes.tcp_dst]     = 'tcp_dst'
        d[MatchTypes.udp_src]     = 'udp_src'
        d[MatchTypes.udp_dst]     = 'udp_dst'
        d[MatchTypes.icmpv4_code] = 'icmpv4_code'
        d[MatchTypes.icmpv4_type] = 'icmpv4_type'
        d[MatchTypes.arp_op]      = 'arp_op'
        d[MatchTypes.arp_spa]     = 'arp_spa'
        d[MatchTypes.arp_tpa]     = 'arp_tpa'
        d[MatchTypes.arp_sha]     = 'arp_sha'
        d[MatchTypes.arp_tha]     = 'arp_tha'

        return d[match_type]

    def __str__(self: MatchTypes) -> str:
        return MatchTypes.to_string(self)

class ActionTypes(Enum):
    Output      = 0
    SetField    = 1
    GotoTable   = 2

    @staticmethod
    def to_string(action_type: ActionTypes) -> str:
        lookup = {}
        lookup[ActionTypes.Output]       = 'OUTPUT'
        lookup[ActionTypes.SetField]     = 'SET_FIELD'
        lookup[ActionTypes.GotoTable]    = 'GOTO_TABLE'
        return lookup[action_type]

    def __str__(self: ActionTypes) -> str:
        return ActionTypes.to_string(self)

class Match:
    """
    Class: Match
    Purpose: Wrapper for instances of OpenFlow Match Criteria represented as
    key-value pairs.
    """
    
    def __init__(self: Match, match_type: MatchTypes, match_value: Match) -> None:
        self.match_dict = {}
        self.match_str = str(match_type)
        self.match_dict[self.match_str] = match_value

    def get_match_params(self: Match) -> Dict[str, Match]:
        return self.match_dict

    def __str__(self: Match) -> str:
        str_rep = ('Match Type: %s, Match Value: %s' 
                    % (self.match_str, str(self.match_dict)))
        return str_rep

    def add_criteria( self          : Match
                    , match_type    : MatchTypes
                    , match_value   : Match ) -> None:
        match_str = str(match_type)
        self.match_dict[match_str] = match_value

class Action:
    
    def __init__( self          : Action
                , action_type   : ActionTypes
                , action_values : Any ) -> None:
        self.action_type = action_type
        self.action_values = action_values

    def get_dict(self: Action) -> Dict[str, str]:
        type_str = str(self.action_type)
        ser = {}
        ser['type'] = type_str
        for act_key, act_val in self.action_values.items():
            ser[act_key] = act_val
        return ser

    def __str__(self: Action) -> str:
        str_rep = 'Action Type: %s\n' % str(self.action_type)
        for k, v in self.action_values.items():
            str_rep += '\t%s: %s\n' % (k, v)
        return str_rep
