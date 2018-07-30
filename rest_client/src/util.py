import re

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