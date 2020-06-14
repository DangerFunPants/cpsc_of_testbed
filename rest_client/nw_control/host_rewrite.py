
import pathlib      as path
import json         as json

import nw_control.params        as cfg
import nw_control.host_mapper   as hm
import nw_control.util          as util
import paramiko                 as ssh
import scp                      as scp

class CommandResult:
    def __init__(self, stdin, stdout, stderr, pid):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pid = pid

    def read_stdout(self):
        return self.stdout.read().decode("utf-8")

    def read_stderr(self):
        return self.stdout.read().decode("utf-8")

class Host:
    """
    Class: Host
    Purpose: Encapsulate parameters and functionality related to individual 
    end hosts. Will allow consumers to run shell commands on the host.
    """

    def __init__( self
                , hostname
                , remote_username
                , remote_password
                , host_id
                , mapper
                , ssh_port=22):
        self.hostname           = hostname
        self.remote_username    = remote_username
        self.remote_password    = remote_password
        self.host_id            = host_id
        self.ssh_port           = ssh_port
        self.mapper             = mapper
        self.host_ip            = self.mapper.resolve_hostname(self.hostname)
        self.ssh_tunnel         = None

    def connect(self):
        if self.ssh_tunnel:
            self.ssh_tunnel.close()
        self.ssh_tunnel = ssh.SSHClient()
        self.ssh_tunnel.set_missing_host_key_policy(ssh.AutoAddPolicy())
        self.ssh_tunnel.connect(self.host_ip, self.ssh_port, username=self.remote_username,
                password = self.remote_password)

    def disconnect(self):
        if self.ssh_tunnel:
            self.ssh_tunnel.close()
        self.ssh_tunnel = None

    def exec_on_remote(self, command_str):
        if not self.ssh_tunnel:
            self.connect()
        stdin, stdout, stderr = self.ssh_tunnel.exec_command(command_str)
        return stdin, stdout, stderr

    def run(self, command_str):
        stdin, stdout, stderr = self.exec_on_remote(command_str)
        pid = None
        return CommandResult(stdin, stdout, stderr, pid)

    def run_async(self, command_str):
        stdin, stdout, stderr = self.exec_on_remote(f"( {command_str} ) & echo $! > /tmp/last-proc.pid") 
        pid = int(self.get_file(path.Path("/tmp/last-proc.pid")))
        return CommandResult(stdin, stdout, stderr, pid)

    def get_file(self, path_like):
        if not self.ssh_tunnel:
            self.connect()

        scp_client = scp.SCPClient(self.ssh_tunnel.get_transport())
        scp_client.get(str(path_like))
        file_contents = path.Path(path_like.name).read_text()
        return file_contents

    def ping(self, remote_host_ip, count=4):
        ping_command = f"ping -c {count} {remote_host_ip}"
        return self.run(ping_command)

class MininetHost(Host):
    TRAFFIC_GEN_ROOT_DIR = path.Path("/home/alexj/repos/cpsc_of_testbed/traffic_generation/")
    TRAFFIC_SERVER_BIN_PATH = TRAFFIC_GEN_ROOT_DIR / "traffic_server.py"
    TRAFFIC_GEN_BIN_PATH = TRAFFIC_GEN_ROOT_DIR / "traffic_gen.py"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_proc = None
        self.client_proc = None
        self.configured_flows = []

    def start_traffic_generation_server(self):
        self.server_proc = self.run_async(
                f"{str(MininetHost.TRAFFIC_SERVER_BIN_PATH)} -host {self.host_id} -source_addr {self.host_ip}")

    def stop_traffic_generation_server(self):
        if self.server_proc:
            self.run(f"kill -s SIGINT {self.server_proc.pid}")

    def configure_flow( self
                      , tx_rate
                      , tx_rate_std_dev
                      , traffic_model
                      , dest_ip
                      , dest_port
                      , k_matrix
                      , time_slice_duration
                      , tag_values
                      , packet_length = 1066):
        client_args = { "dest_port"     : dest_port
                      , "dest_addr"     : dest_ip
                      , "prob_mat"      : k_matrix
                      , "tx_rate"       : tx_rate
                      , "variance"      : tx_rate_std_dev
                      , "traffic_model" : traffic_model
                      , "packet_len"    : packet_length
                      , "src_host"      : self.host_id
                      , "time_slice"    : time_slice_duration
                      , "tag_value"     : tag_values
                      , "source_addr"   : self.host_ip
                      }
        self.configured_flows.append(client_args)

    def start_traffic_generation_client(self):
        if len(self.configured_flows) == 0:
            return
        args = f"{str(MininetHost.TRAFFIC_GEN_BIN_PATH)} '{json.dumps(self.configured_flows)}'"
        print("client args:")
        print(args)
        self.client_proc = self.run_async(args)

    def stop_traffic_generation_client(self):
        if self.client_proc:
            self.run(f"kill -s SIGINT {self.client_proc.pid}")

