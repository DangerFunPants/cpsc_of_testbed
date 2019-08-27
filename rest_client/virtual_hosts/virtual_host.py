
import requests             as req
import urllib.parse         as url
import json                 as json
import subprocess           as subprocess
import netifaces            as netifaces
import pprint               as pp

import nw_control.params            as cfg
import virtual_hosts.params         as vhost_cfg

class VirtualHost: 
    def __init__( self
                , actual_host_mac
                , actual_host_ip
                , virtual_host_mac
                , virtual_host_ip
                , ingress_node_device_id
                , token):
        self._actual_host_mac           = actual_host_mac
        self._actual_host_ip            = actual_host_ip
        self._virtual_host_mac          = virtual_host_mac
        self._virtual_host_ip           = virtual_host_ip
        self._ingress_node_device_id    = ingress_node_device_id
        self._token                     = token

    @staticmethod
    def _install_virtual_host( actual_host_mac
                             , actual_host_ip
                             , virtual_host_mac
                             , virtual_host_ip
                             , ingress_node_device_id):
        request_json = { "ingressNode"              : ingress_node_device_id
                       , "virtualHostMacAddress"    : virtual_host_mac
                       , "actualHostMacAddress"     : actual_host_mac
                       , "virtualHostIpAddress"     : virtual_host_ip
                       , "actualHostIpAddress"      : actual_host_ip
                       }
        pp.pprint(request_json)

        request_url = url.urljoin(vhost_cfg.onos_url.geturl(), 
                "virtual-hosts/v1/create-virtual-host")
        create_virtual_host_request = req.post(request_url, json=request_json,
                auth=cfg.ONOS_API_CREDENTIALS)
        if not create_virtual_host_request:
            raise ValueError("Failed to create virtual host. Status %d %s" %
                    (create_virtual_host_request.status_code, create_virtual_host_request.reason))
        response_json = create_virtual_host_request.json()
        return response_json["virtual-host-id"]

    @staticmethod
    def _initialize_local_network_interface(iface_name, actual_host_ip_address):
        def build_ip_addr_add_cmd(password, actual_host_ip_address, mask_length, iface_name):
            ip_addr_add_cmd = ("ip addr add %s/%d dev %s" %
                    (actual_host_ip_address, mask_length, iface_name)).split(" ")
            return ip_addr_add_cmd

        ip_addr_add_cmd = build_ip_addr_add_cmd(vhost_cfg.password, actual_host_ip_address,
                24, iface_name)
        proc_result = subprocess.run(ip_addr_add_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        if proc_result.returncode != 0:
            raise ValueError("Failed to initialize local network interface with command: %s" %
                    (ip_addr_add_cmd))
        interface_mac_address = netifaces.ifaddresses(iface_name)[netifaces.AF_LINK][0]
        return interface_mac_address["addr"]
         
    @staticmethod
    def create_virtual_host( virtual_host_mac
                           , virtual_host_ip
                           , actual_host_ip
                           , ingress_node_device_id):
        actual_host_mac = VirtualHost._initialize_local_network_interface(vhost_cfg.iface_name, 
                actual_host_ip)
        virtual_host_token = VirtualHost._install_virtual_host(actual_host_mac, actual_host_ip,
                virtual_host_mac, virtual_host_ip, ingress_node_device_id)
        the_virtual_host = VirtualHost(actual_host_mac, actual_host_ip,
                virtual_host_mac, virtual_host_ip, ingress_node_device_id, virtual_host_token)
        return the_virtual_host

    def destroy_virtual_host(self):
        request_url = url.urljoin(vhost_cfg.onos_url.geturl(), 
                "virtual-hosts/v1/destroy-virtual-host?virtual-host-id=%s" % self.token)
        destroy_host_request = req.post(request_url, auth=cfg.ONOS_API_CREDENTIALS)
        if not destroy_host_request:
            raise ValueError("Failed to destroy virtual host with token %s. %d %s" %
                    (self.token, destroy_host_request.status_code, destroy_host_request.reason))
        self._remove_virtual_host_ip_address()


    def _remove_virtual_host_ip_address(self):
        def build_ip_addr_del_cmd(iface_name, actual_host_ip_address, mask_length):
            ip_addr_del_cmd = ("ip addr del %s/%d dev %s" %
                    (actual_host_ip_address, mask_length, iface_name))
            return ip_addr_del_cmd.split(" ")

        ip_addr_del_cmd = build_ip_addr_del_cmd(vhost_cfg.iface_name, self.actual_host_ip, 24)
        proc_result = subprocess.run(ip_addr_del_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        if proc_result.returncode != 0:
            raise ValueError("Failed to remove IP address with command %s" % ip_addr_del_cmd)

    @property
    def actual_host_mac(self):
        return self._actual_host_mac

    @property
    def actual_host_ip(self):
        return self._actual_host_ip

    @property
    def virtual_host_mac(self):
        return self._virtual_host_mac

    @property
    def virtual_host_ip(self):
        return self._virtual_host_ip

    @property
    def ingress_node_device_id(self):
        return self._ingress_node_device_id

    @property
    def token(self):
        return self._token

    def __str__(self):
        s = "Virtual Host %s" % self.token
        s += "\tActual Host MAC     | %s" % self.actual_host_mac
        s += "\tActual Host IP      | %s" % self.actual_host_ip
        s += "\tVirtual Host MAC    | %s" % self.virtual_host_mac
        s += "\tVirtual Host IP     | %s" % self.virtual_host_ip
        return s
