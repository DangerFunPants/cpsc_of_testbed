
import pathlib      as path
import json         as json
import pickle       as pickle
import time         as time

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
        self.stop_traffic_generation_server()
        self.stop_traffic_generation_client()
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
        time.sleep(3)
        pid = int(self.get_file(path.Path("/tmp/last-proc.pid"), lambda fp: fp.read_text()))
        return CommandResult(stdin, stdout, stderr, pid)

    def get_file(self, path_like, reader):
        if not self.ssh_tunnel:
            self.connect()

        scp_client = scp.SCPClient(self.ssh_tunnel.get_transport())
        output_path = path.Path("/tmp") / "cpsc-of-testbed-remote-transfer-file.dat"
        scp_client.get(str(path_like), local_path=output_path)
        return reader(output_path)

    def put_file(self, path_like, output_path):
        if not self.ssh_tunnel:
            self.connect()
        scp_client = scp.SCPClient(self.ssh_tunnel.get_transport())
        scp_client.put(path_like, output_path)

    def ping(self, remote_host_ip, count=4):
        ping_command = f"ping -c {count} {remote_host_ip}"
        return self.run(ping_command)

class MininetHost(Host):
    TRAFFIC_GEN_ROOT_DIR = path.Path("/home/alexj/repos/cpsc_of_testbed/traffic_generation/")
    TRAFFIC_SERVER_BIN_PATH = TRAFFIC_GEN_ROOT_DIR / "traffic_server.py"
    TRAFFIC_GEN_BIN_PATH = TRAFFIC_GEN_ROOT_DIR / "traffic_gen.py"

    def __init__(self, host_ip, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_ip = host_ip
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

    def configure_flow_with_precomputed_transmit_rates( self
                                                      , rate_list
                                                      , destination_ip
                                                      , destination_port_number
                                                      , k_matrix
                                                      , host_number
                                                      , time_slice_duration
                                                      , tag_values
                                                      , packet_length = 1066):
        client_args = { "dest_port"         : destination_port_number
                      , "dest_addr"         : destination_ip
                      , "prob_mat"          : k_matrix
                      , "transmit_rates"    : rate_list
                      , "traffic_model"     : "precomputed"
                      , "packet_len"        : packet_length
                      , "src_host"          : host_number
                      , "time_slice"        : time_slice_duration
                      , "tag_value"         : tag_values
                      }
        self.configured_flows.append(client_args)

    def configure_bulk_transfer_request( self
                                       , request_transmit_rates
                                       , request_deadline
                                       , total_data_volume
                                       , number_of_timeslots
                                       , destination_ip
                                       , destination_port_number
                                       , source_ip_address
                                       , k_matrix
                                       , host_number
                                       , time_slice_duration
                                       , tag_values
                                       , packet_length = 1066):
        client_args = { "request_transmit_rates"    : request_transmit_rates
                      , "request_deadline"          : request_deadline
                      , "total_data_volume"         : total_data_volume
                      , "number_of_timeslots"       : number_of_timeslots
                      , "dest_addr"                 : destination_ip
                      , "dest_port"                 : destination_port_number
                      , "source_ip_address"         : source_ip_address
                      , "prob_mat"                  : k_matrix
                      , "traffic_model"             : "request-based"
                      , "packet_len"                : packet_length
                      , "src_host"                  : host_number
                      , "time_slice"                : time_slice_duration
                      , "tag_value"                 : tag_values
                      }
        self.configured_flows.append(client_args)

                                       

    def start_traffic_generation_client(self):
        if len(self.configured_flows) == 0:
            return
        
        args_file_path = path.Path(f"/tmp/host-{self.host_id}-traffic-gen-args.json")
        args = f"{str(MininetHost.TRAFFIC_GEN_BIN_PATH)} {str(args_file_path)}"
        args_file_path.write_text(json.dumps(self.configured_flows))
        self.put_file(str(args_file_path), str(args_file_path))
        self.client_proc = self.run_async(args)

    def stop_traffic_generation_client(self):
        if self.client_proc:
            self.run(f"kill -s SIGINT {self.client_proc.pid}")

    def get_sender_results(self):
        sender_file_path = path.Path(f"/tmp/sender_{self.host_id}.p")
        try:
            sender_results = self.get_file(sender_file_path, lambda fp: pickle.load(fp.open("rb")))
        except Exception:
            raise ValueError(f"Couldn't find file {str(sender_file_path)} on host with IP Address {self.host_ip}.")
        return sender_results

    def get_receiver_results(self):
        receiver_file_path = path.Path(f"/tmp/receiver_{self.host_id}.p")
        try:
            receiver_results = self.get_file(receiver_file_path, lambda fp: pickle.load(fp.open("rb")))
        except Exception:
            raise ValueError(
                    f"Couldn't find file {str(receiver_file_path)} on host with IP Address {self.host_ip}.")
        return receiver_results
        

