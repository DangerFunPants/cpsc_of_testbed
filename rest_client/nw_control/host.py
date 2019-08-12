
import paramiko                     as ssh
import pathlib                      as path
import subprocess                   as subprocess
import pickle                       as pickle

import nw_control.util              as util
import nw_control.params            as cfg
import nw_control.host_mapper       as hm

from functools import reduce

class Host:
    """
    Class: Host
    Purpose: Encapsulate parameters and functionality related to individual 
    end hosts. Will allow consumers to run bash commands on the host.
    """

    def __init__( self
                , host_name
                , rem_uname
                , rem_pw
                , host_id
                , ssh_port=22 ):
        self.host_name      = host_name
        self.ssh_port       = ssh_port
        self.rem_uname      = rem_uname
        self.rem_pw         = rem_pw
        self.ssh_tunnel     = None
        self.host_id        = host_id

        if util.is_ip_addr(host_name):
            self.host_ip = host_name
        else:
            mapper = hm.HostMapper([cfg.man_net_dns_ip], 
                cfg.of_controller_ip, cfg.of_controller_port, domain='hosts.sdn.')
            self.host_ip = mapper.resolve_hostname(self.host_name)

    def connect(self):
        self.ssh_tunnel = ssh.SSHClient()
        self.ssh_tunnel.set_missing_host_key_policy(ssh.AutoAddPolicy())
        self.ssh_tunnel.connect(self.host_ip, self.ssh_port, username=self.rem_uname, password=self.rem_pw)
    
    def disconnect(self):
        self.ssh_tunnel.close()
        self.ssh_tunnel = None

    def exec_command(self, command):
        if self.ssh_tunnel:
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
        else:
            self.connect()
            _,stdout,stderr = self.ssh_tunnel.exec_command(command)
            self.disconnect()
        return (stdout,stderr)

    def ping(self, remote_host, count=4): 
        ping_command = 'ping -c %d %s' % (count, remote_host)
        stdout, stderr = self.exec_command(ping_command)
        return (stdout, stderr)

class TrafficGenHost(Host):

    BIN_DIR                 = '/home/alexj/traffic_generation/' 
    COUNT_DIR               = '/home/alexj/packet_counts/'
    TMP_OUTPUT_DIRECTORY    = path.Path("/tmp/")

    def __init__( self
                , host_name
                , rem_uname
                , rem_pw
                , ssh_port = 22 ):
        Host.__init__(self, host_name, rem_uname, rem_pw, ssh_port)
        self._clients = []

    def _add_client(self, client_params):
        self._clients.append(client_params)

    def remove_all_files(self, path, ext):
        comm_str = 'rm -f %s*.%s' % (path, ext)
        self.exec_command(comm_str)
    
    def start_client( self
                    , mu
                    , sigma
                    , traffic_model
                    , dest_ip 
                    , port_no 
                    , k_mat 
                    , host_no 
                    , slice ):

        self.remove_all_files(TrafficGenHost.COUNT_DIR, 'txt')
        start_comm = '%s/traffic_gen.py' % TrafficGenHost.BIN_DIR
        k_mat_str = reduce(lambda l, r : str(l) + ' ' + str(r), k_mat)
        args = [ ('-a %s' % dest_ip)
               , ('-p %s' % port_no)
               , ('-k %s' % k_mat_str)
               , ('-t %s' % mu)
               , ('-s %s' % sigma)
               , ('-c %s' % traffic_model)
               , ('-host %s' % host_no)
               , ('-slice %s' % slice)
               , ('-n %s' % 1)
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        comm_str += ' &'
        return self.exec_command(comm_str)

    def stop_client(self):
        command_str = (
            'ps ax | grep -i traffic_gen.py | grep -v grep | awk \'{print $1}\' | xargs -n1 -I {} kill -s SIGINT {}'
        )
        return self.exec_command(command_str)
    
    def start_server(self):
        self.remove_all_files(TrafficGenHost.COUNT_DIR, 'p')
        start_comm = '%s/traffic_server.py' % TrafficGenHost.BIN_DIR
        args = [ ('-host %s' % str(self.host_id))
               ]
        comm_str = util.inject_arg_opts(start_comm, args)
        comm_str += ' &'
        return self.exec_command(comm_str)

    def stop_server(self):
        command_str = (
            'ps ax | grep -i traffic_server.py | grep -v grep | awk \'{print $1}\' | xargs -n1 -I {} kill -s SIGINT {}'
        )
        return self.exec_command(command_str)

    def retrieve_client_files(self, dst_dir):
        local_ip = self.get_local_ip()
        command = 'sshpass -pubuntu scp -o StrictHostKeyChecking=no -r %ssender_*.p ubuntu@%s:%s' % (self.COUNT_DIR, local_ip, dst_dir)
        self.exec_command(command)

    def retrieve_server_files(self, dst_dir):
        local_ip = self.get_local_ip()
        command = 'sshpass -pubuntu scp -o StrictHostKeyChecking=no -r %sreceiver_*.p ubuntu@%s:%s' % (self.COUNT_DIR, local_ip, dst_dir)
        self.exec_command(command)

    def retrieve_end_host_results(self):
        host_string = "alexj@%s:%s" % (self.host_ip, TrafficGenHost.COUNT_DIR)
        sender_file = "sender_%d.p" % self.host_id
        receiver_file = "receiver_%d.p" % self.host_id

        for file_name in [sender_file, receiver_file]:
            scp_cmd = "sshpass -pcpsc scp %s/%s %s" % (host_string, file_name,
                    TrafficGenHost.TMP_OUTPUT_DIRECTORY)
            subprocess.run(scp_cmd.split(" "))
        
        receiver_file_path = TrafficGenHost.TMP_OUTPUT_DIRECTORY / receiver_file
        receiver_results = {}
        if receiver_file_path.exists():
            with receiver_file_path.open("rb") as fd:
                receiver_results = pickle.load(fd)

        modified_receiver_results = []
        for (ip_address, port_number), packet_count in receiver_results.items():
            modified_receiver_results.append([ip_address, port_number, packet_count])

        
        sender_file_path = TrafficGenHost.TMP_OUTPUT_DIRECTORY / sender_file
        sender_results = {}
        if sender_file_path.exists():
            with sender_file_path.open("rb") as fd:
                sender_results = pickle.load(fd)

        return modified_receiver_results, dict(sender_results)

    def get_local_ip(self):
        mapper = hm.HostMapper([cfg.man_net_dns_ip], cfg.of_controller_ip,
            cfg.of_controller_port, domain='hosts.sdn.')
        local_ip = mapper.resolve_hostname('sdn.cpscopenflow1')
        return local_ip

    def configure_client( self
                        , mu 
                        , sigma
                        , traffic_model
                        , dest_ip
                        , port_no
                        , k_mat
                        , host_no
                        , slice
                        , tag_value
                        , pkt_len=1066 ):
        client_args = { "dest_port"         : port_no
                      , "dest_addr"         : dest_ip
                      , "prob_mat"          : k_mat
                      , "tx_rate"           : mu
                      , "variance"          : ( sigma ** 2 )
                      , "traffic_model"     : traffic_model
                      , "packet_len"        : pkt_len
                      , "src_host"          : host_no
                      , "time_slice"        : slice
                      , "tag_value"         : tag_value
                      }
        self._add_client(client_args)

    def configure_precomputed_client( self
                                    , rate_list
                                    , destination_ip
                                    , destination_port_number
                                    , k_mat
                                    , host_number
                                    , time_slice_duration
                                    , tag_values
                                    , packet_length=1066):
        client_args = { "dest_port"         : destination_port_number
                      , "dest_addr"         : destination_ip
                      , "prob_mat"          : k_mat
                      , "transmit_rates"    : rate_list
                      , "traffic_model"     : "precomputed"
                      , "packet_len"        : packet_length
                      , "src_host"          : host_number
                      , "time_slice"        : time_slice_duration
                      , "tag_value"         : tag_values
                      }
        self._add_client(client_args)

    def start_clients(self):
        command_args = '\"%s\"' % str(self._clients)
        start_comm = '%s/traffic_gen.py' % TrafficGenHost.BIN_DIR
        comm_str = util.inject_arg_opts(start_comm, [command_args])
        comm_str += "&>/home/alexj/traffic-gen-log.txt"
        comm_str += ' &'
        return self.exec_command(comm_str)

    @staticmethod
    def create_host(hostname, host_id):
        default_host = TrafficGenHost(hostname, "alexj", "cpsc", host_id)
        return default_host
