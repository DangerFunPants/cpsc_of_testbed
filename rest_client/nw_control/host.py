import paramiko as ssh
from . import util
from . import params

from functools import reduce

from . import host_mapper       as hm
from . import params            as cfg

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
                , ssh_port=22 ):
        self.host_name = host_name
        self.ssh_port = ssh_port
        self.rem_uname = rem_uname
        self.rem_pw = rem_pw
        self.ssh_tunnel = None

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

    BIN_DIR = '/home/alexj/traffic_generation/' 
    COUNT_DIR = '/home/alexj/packet_counts/'

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
    
    def start_server(self, host_no):
        self.remove_all_files(TrafficGenHost.COUNT_DIR, 'p')
        start_comm = '%s/traffic_server.py' % TrafficGenHost.BIN_DIR
        args = [ ('-host %s' % str(host_no))
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

    def start_clients(self):
        command_args = '\"%s\"' % str(self._clients)
        start_comm = '%s/traffic_gen.py' % TrafficGenHost.BIN_DIR
        comm_str = util.inject_arg_opts(start_comm, [command_args])
        comm_str += ' &'
        return self.exec_command(comm_str)

    @staticmethod
    def create_host(hostname):
        default_host = TrafficGenHost(hostname, "alexj", "cpsc")
        return default_host
