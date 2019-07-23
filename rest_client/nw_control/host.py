import paramiko as ssh
from . import util
from . import params
from . import host_mapper 

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
