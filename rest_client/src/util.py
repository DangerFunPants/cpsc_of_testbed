import re
from functools import reduce
import host_mapper as hm

from typing import List, Dict, Any, Callable

def is_ip_addr(data: str) -> bool:
    ip_regex = re.compile('([0-9]{1,3}\.){3}([0-9]{1,3})')
    if ip_regex.match(data):
        return True
    else:
        return False

def dpid_fmt(dpid: str) -> str:
    return '{:016x}'.format(dpid)

def set_field(d: Dict[Any, Any], k: Any, v:Any) -> Dict[Any, Any]:
    if v is not None:
        d[k] = v
    return d

def sw_name_to_no(sw_name: str) -> str:
    """
    This will only handle swith names of the form:
        of_<sw_no>
    """
    sw_no = sw_name.split('_')[1]
    return sw_no

def inject_arg_opts( command_str    : str
                   , arg_list       : List[str] ) -> str:
    """
    Combine a command with a list of strings
    representing the arguments to the command in POSIX style
    """
    return reduce(lambda l, r : l + ' ' + r, arg_list, command_str)

def mk_pretty_sw_dict( sw_dict  : Dict[Any, Any]
                     , mapper   : hm.HostMapper
                     , reader   : Callable[[Any], str] = None
                     , writer   : Callable[[str, str], Any] = None ) -> Dict[Any, Any]:
    """
    Takes a dictionary whose keys are DPIDs represented as 
    integers and returns a dict whose keys are friendly
    switch names.
    """
    res = {}
    for k, v in sw_dict.items():
       friendly_name = mapper.map_dpid_to_sw(reader(k))
       res[writer(friendly_name, k)] = v
    return res

