from enum import Enum
from functools import (reduce)
from . import util

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

    def __init__( self
                , dpid
                , cookie = None
                , cookie_mask = None
                , table_id = None
                , idle_timeout = None
                , hard_timeout = None
                , priority = None
                , flags = None
                ):
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

    def add_match(self, match):
        for k, v in match.get_match_params().items():
            self.match[k] = v
    
    def add_action(self, action):
        d = action.get_dict()
        self.actions = self.actions + [d]

    def get_json(self):
        d = {}
        d['dpid'] = self.dpid
        d = set_field(d, 'dpid', self.dpid)
        d = set_field(d, 'cookie', self.cookie)
        d = set_field(d, 'cookie_mask', self.cookie_mask)
        d = set_field(d, 'table_id', self.table_id)
        d = set_field(d, 'idle_timeout', self.idle_timeout)
        d = set_field(d, 'hard_timeout', self.hard_timeout)
        d = set_field(d, 'priority', self.priority)
        d = set_field(d, 'flags', self.flags)

        d['match'] = self.match
        d['actions'] = self.actions
        return d

    def __str__(self):
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
    def to_string(match_type):
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

    def __str__(self):
        return MatchTypes.to_string(self)

class ActionTypes(Enum):
    Output      = 0
    SetField    = 1
    GotoTable   = 2

    @staticmethod
    def to_string(action_type):
        d = {}
        d[ActionTypes.Output]       = 'OUTPUT'
        d[ActionTypes.SetField]     = 'SET_FIELD'
        d[ActionTypes.GotoTable]    = 'GOTO_TABLE'
        return d[action_type]

    def __str__(self):
        return ActionTypes.to_string(self)

class Match:
    """
    Class: Match
    Purpose: Wrapper for instances of OpenFlow Match Criteria represented as
    key-value pairs.
    """
    
    def __init__(self, match_type, match_value):
        self.match_dict = {}
        match_str = str(match_type)
        self.match_dict[match_str] = match_value

    def get_match_params(self):
        return self.match_dict

    def __str__(self):
        str_rep = ('Match Type: %s, Match Value: %s' 
                    % (str(self.match_type), str(self.match_value)))
        return str_rep

    def add_criteria(self, match_type, match_value):
        match_str = str(match_type)
        self.match_dict[match_str] = match_value


class Action:
    
    def __init__(self, action_type, action_values):
        self.action_type = action_type
        self.action_values = action_values

    def get_dict(self):
        type_str = str(self.action_type)
        d = {}
        d['type'] = type_str
        for k,v in self.action_values.items():
            d[k] = v
        return d

    def __str__(self):
        str_rep = 'Action Type: %s\n' % str(self.action_type)
        for k, v in self.action_values.items():
            str_rep += '\t%s: %s\n' % (k, v)
        return str_rep
