
import requests                     as req
import urllib.parse                 as url
import json                         as json
import subprocess                   as subprocess
import netifaces                    as netifaces
import pprint                       as pp
import signal                       as signal
import pathlib                      as path
import operator                     as operator

import nw_control.params            as cfg
import virtual_hosts.params         as vhost_cfg

from functools                      import reduce

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
            raise ValueError("Failed to create virtual host with IP Address %s. Status %d %s" %
                    (virtual_host_ip, create_virtual_host_request.status_code, 
                        create_virtual_host_request.reason))
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
            print(proc_result.stdout.decode("utf-8"))
            raise ValueError("Failed to initialize local network interface with command: %s" %
                    (ip_addr_add_cmd))
        interface_mac_address = netifaces.ifaddresses(iface_name)[netifaces.AF_LINK][0]
        return interface_mac_address["addr"]

    @staticmethod
    def _remove_local_network_interface(iface_name, actual_host_ip_address):
        def build_del_ip_addr_cmd(password, actual_host_ip_address, mask_length, iface_name):
            ip_addr_del_cmd = ("ip addr del %s/%d dev %s" %
                    (actual_host_ip_address, mask_length, iface_name)).split(" ")
            return ip_addr_del_cmd

        ip_addr_del_cmd = build_del_ip_addr_cmd(vhost_cfg.password, actual_host_ip_address,
                24, iface_name)
        proc_result = subprocess.run(ip_addr_del_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        if proc_result.returncode != 0:
            raise ValueError("Failed to remove local network interface with command: %s" %
                    (ip_addr_del_cmd))
    
    @staticmethod
    def _uninstall_virtual_host(virtual_host_token):
        request_url = url.urljoin(vhost_cfg.onos_url.geturl(), 
                "virtual-hosts/v1/destroy-virtual-host?virtual-host-id=%s" % virtual_host_token)
        destroy_host_request = req.post(request_url, auth=cfg.ONOS_API_CREDENTIALS)
        if not destroy_host_request:
            raise ValueError("Failed to destroy virtual host with token %s. %d %s" %
                    (virtual_host_token, 
                        destroy_host_request.status_code, destroy_host_request.reason))
         
    @staticmethod
    def initialize_virtual_host_persistent_state( virtual_host_mac
                                                , virtual_host_ip
                                                , actual_host_ip
                                                , ingress_node_device_id):
        actual_host_mac     = None
        virtual_host_token  = None
        try:
            actual_host_mac = VirtualHost._initialize_local_network_interface(vhost_cfg.iface_name, 
                    actual_host_ip)
            virtual_host_token = VirtualHost._install_virtual_host(actual_host_mac, actual_host_ip,
                    virtual_host_mac, virtual_host_ip, ingress_node_device_id)
        except Exception as ex:
            if actual_host_mac != None:
                VirtualHost._remove_local_network_interface(vhost_cfg.iface_name,
                        actual_host_ip)
            if virtual_host_token != None:
                VirtualHost._uninstall_virtual_host(virtual_host_token)
            raise ex

        return actual_host_mac, virtual_host_token

    def destroy_virtual_host(self):
        VirtualHost._uninstall_virtual_host(self.token)
        VirtualHost._remove_local_network_interface(vhost_cfg.iface_name, self.actual_host_ip) 

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


class TrafficGenerationVirtualHost(VirtualHost):
    BIN_DIR = path.Path("/home/cpsc-net-user/repos/cpsc_of_testbed/traffic_generation/")

    def __init__(self, host_id, *args):
        super(TrafficGenerationVirtualHost, self).__init__(*args)
        self._host_id                       = host_id
        self._traffic_gen_server_process    = None
        self._traffic_gen_client_process    = None
        self._configured_flows              = []

    @property
    def host_id(self):
        return self._host_id
    
    @property
    def configured_flows(self):
        return self._configured_flows

    @staticmethod
    def create_virtual_host( host_id
                           , virtual_host_mac
                           , virtual_host_ip
                           , actual_host_ip
                           , ingress_node_device_id):
        actual_host_mac, virtual_host_token = \
                VirtualHost.initialize_virtual_host_persistent_state(virtual_host_mac, 
                        virtual_host_ip, actual_host_ip, ingress_node_device_id)
        the_virtual_host = TrafficGenerationVirtualHost(host_id, actual_host_mac, actual_host_ip,
                virtual_host_mac, virtual_host_ip, ingress_node_device_id, virtual_host_token)
        return the_virtual_host

    def start_traffic_generation_server(self):
        traffic_gen_server_path = TrafficGenerationVirtualHost.BIN_DIR / "traffic_server.py"
        args = [ str(traffic_gen_server_path)
               , "-host"            , str(self.host_id)
               , "-source_addr"     , self.actual_host_ip
               ]
        traffic_gen_server_process = subprocess.Popen(args, 
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self._traffic_gen_server_process = traffic_gen_server_process 

    def stop_traffic_generation_server(self):
        if self._traffic_gen_server_process == None:
            raise ValueError("Attempting to stop traffic generation server before starting it.")
        self._traffic_gen_server_process.send_signal(signal.SIGINT)

    def configure_flow( self
                      , tx_rate
                      , tx_rate_std_dev
                      , traffic_model
                      , dest_ip
                      , port_num
                      , k_mat
                      , time_slice
                      , tag_values
                      , pkt_len=1066):

        client_args = { "dest_port"         : port_num
                      , "dest_addr"         : dest_ip
                      , "prob_mat"          : k_mat
                      , "tx_rate"           : tx_rate
                      , "variance"          : tx_rate_std_dev**2
                      , "traffic_model"     : traffic_model
                      , "packet_len"        : pkt_len
                      , "src_host"          : self.host_id
                      , "time_slice"        : time_slice
                      , "tag_value"         : tag_values
                      , "source_addr"       : self.actual_host_ip
                      }
        self._configured_flows.append(client_args)

    def start_traffic_generation_client(self):
        # If no flows have been configured, starting the traffic generation client does
        # nothing.
        if len(self.configured_flows) > 0:
            traffic_gen_client_path = TrafficGenerationVirtualHost.BIN_DIR / "traffic_gen.py"
            args = [ str(traffic_gen_client_path)
                   , json.dumps(self.configured_flows)
                   ]
            # print(reduce(lambda v1, v2: " " + v1 + " " + v2, args))
            traffic_gen_client_process = subprocess.Popen(args,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self._traffic_gen_client_process = traffic_gen_client_process

    def stop_traffic_generation_client(self):
        # If no flows were configured, stopping the client does nothing.
        if len(self.configured_flows) == 0:
            return

        # Can't stop the client if it was never started.
        if self._traffic_gen_client_process == None:
            raise ValueError("Attempting to stop traffic generation client before starting it.")

        self._traffic_gen_client_process.send_signal(signal.SIGINT)
        if self._traffic_gen_client_process.returncode != 0:
            std_out, std_err = self._traffic_gen_client_process.communicate()
            print("Host %d traffic generation failed with error: " % self.host_id)
            print(std_out.decode("utf-8"))
            print("")


    def destroy_virtual_host(self):
        super().destroy_virtual_host()
        if self._traffic_gen_client_process != None:
            self.stop_traffic_generation_client()

        if self._traffic_gen_server_process != None:
            self.stop_traffic_generation_server()

class PathHoppingSender(VirtualHost):
    BIN_DIR = path.Path("/home/cpsc-net-user/repos/mtd-crypto-impl/endpoint/sender")
    
    def __init__(self, host_id, *args):
        super(PathHoppingSender, self).__init__(*args)
        self._host_id               = host_id
        self._sender_process        = None

    @property
    def host_id(self):
        return self._host_id

    @staticmethod
    def create_virtual_host( host_id
                           , virtual_host_mac
                           , virtual_host_ip
                           , actual_host_ip
                           , ingress_node_device_id):
        actual_host_mac, virtual_host_token = \
                VirtualHost.initialize_virtual_host_persistent_state(virtual_host_mac,
                        virtual_host_ip, actual_host_ip, ingress_node_device_id)
        the_virtual_host = PathHoppingSender(host_id, actual_host_mac, actual_host_ip,
                virtual_host_mac, virtual_host_ip, ingress_node_device_id, virtual_host_token)
        return the_virtual_host

    def start_path_hopping_sender( self
                                 , port                 = None
                                 , K                    = None
                                 , N                    = None
                                 , data_file            = None
                                 , message_size         = None
                                 , timestep             = None
                                 , hop_probability      = None
                                 , reliable             = None
                                 , hop_method           = None):

        print("Using data file %s" % data_file)
        sender_args = [ str(PathHoppingSender.BIN_DIR)
                      , "-h"           , self.actual_host_ip
                      , "-p"           , port
                      , "-k"           , K
                      , "-n"           , N
                      , "-file"        , data_file
                      , "-m"           , message_size
                      , "-timestep"    , timestep
                      , "-lambda"      , hop_probability
                      , "-reliable"    , reliable
                      , "-hop"         , hop_method
                      ]

        if self._sender_process != None:
            raise ValueError("Attempting to start sender host after already being started.")

        self._sender_process = subprocess.Popen(sender_args, stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL)

    def stop_path_hopping_sender(self):
        if self._sender_process == None:
            raise ValueError("Attempting to stop path hopping sender without starting it.")

        self._sender_process.terminate()
        _, std_err = self._sender_process.communicate()
        if self._sender_process.returncode != 0:
            print("PathHoppingSender %d failed with error: " % self.host_id)
            print(std_err.decode("utf-8"))
            print("")

    def destroy_virtual_host(self):
        super().destroy_virtual_host()
        if self._sender_process != None:
            self.stop_path_hopping_sender()

class PathHoppingReceiver(VirtualHost):
    BIN_DIR = path.Path("/home/cpsc-net-user/repos/mtd-crypto-impl/endpoint/receiver")
    
    def __init__(self, host_id, *args):
        super(PathHoppingReceiver, self).__init__(*args)
        self._host_id           = host_id
        self._receiver_process  = None

    @property
    def host_id(self):
        return self._host_id

    @staticmethod
    def create_virtual_host( host_id
                           , virtual_host_mac
                           , virtual_host_ip
                           , actual_host_ip
                           , ingress_node_device_id):
        actual_host_mac, virtual_host_token = \
                VirtualHost.initialize_virtual_host_persistent_state(virtual_host_mac, 
                        virtual_host_ip, actual_host_ip, ingress_node_device_id)
        the_virtual_host = PathHoppingReceiver(host_id, actual_host_mac, actual_host_ip,
                virtual_host_mac, virtual_host_ip, ingress_node_device_id, virtual_host_token)
        return the_virtual_host

    def start_path_hopping_receiver( self
                                   , sender_ip              = None
                                   , port                   = None
                                   , data_file              = None
                                   , timestep               = None
                                   , hopping_probability    = None):
        receiver_args = [ str(PathHoppingReceiver.BIN_DIR)
                        , "-h"          , sender_ip
                        , "-p"          , port
                        , "-file"       , data_file
                        , "-timestep"   , timestep
                        , "-lambda"     , hopping_probability
                        , "-local_addr" , self.actual_host_ip
                        ]
        if self._receiver_process != None:
            raise ValueError("Attempting to start receiver host after already being started.")

        self._receiver_process = subprocess.Popen(receiver_args, stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL)

    def stop_path_hopping_receiver(self):
        if self._receiver_process == None:
            raise ValueError("Attempting to stop path hopping receiver without starting it.")
        self._receiver_process.terminate()
        _, std_err = self._receiver_process.communicate()
        if self._receiver_process.returncode != 0:
            print("PathHoppingReceiver %d failed with error: " % self.host_id)
            print(std_err.decode("utf-8"))
            print("")

    def destroy_virtual_host(self):
        super().destroy_virtual_host()
        if self._receiver_process != None:
            self.stop_path_hopping_receiver()

    def wait_until_done(self):
        if self._receiver_process == None:
            raise ValueError("Attempting to wait on path hopping receiver without starting it.")
        return self._receiver_process.wait()




