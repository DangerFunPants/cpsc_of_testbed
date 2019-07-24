
import re       as re
import json     as json

from functools      import reduce

def is_ip_addr(data):
    ip_regex = re.compile('([0-9]{1,3}\.){3}([0-9]{1,3})')
    return ip_regex.match(data)

def dpid_fmt(dpid):
    return '{:016x}'.format(dpid)

def set_field(d, k, v):
    if v is not None:
        d[k] = v
    return d

def sw_name_to_no(sw_name):
    """
    This will only handle swith names of the form:
        of_<sw_no>
    """
    sw_no = sw_name.split('_')[1]
    return sw_no

def inject_arg_opts(command_str, arg_list):
    """
    Combine a command with a list of strings
    representing the arguments to the command in POSIX style
    """
    return reduce(lambda l, r : l + ' ' + r, arg_list, command_str)

def mk_pretty_sw_dict(sw_dict, mapper, reader = None, writer = None):
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

def mbps_to_bps(rate_in_mbps):
    return rate_in_mbps * 10**6

def bytes_per_second_to_mbps(rate_in_bytes_per_second):
    return (rate_in_bytes_per_second * 8) / 10**6

def read_json_from_file(file_path):
    with file_path.open("r") as fd:
        json_str = fd.read()
    return json.loads(json_str)
