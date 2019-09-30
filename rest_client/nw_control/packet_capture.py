
import subprocess       as subprocess
import random           as rand
import pathlib          as path

from collections        import namedtuple

PacketInfo = namedtuple("PacketInfo", 
        "source_ip destination_ip source_port destination_port seq_num share_num timestamp")

def read_literal_from_file(file_path):
    with file_path.open("r") as fd:
        file_bytes = fd.read()
    return eval(file_bytes)

def read_packet_dump_info_from_file(file_path):
    list_literal = read_literal_from_file(file_path)
    packet_infos = [PacketInfo(*t_i) for t_i in list_literal]
    return packet_infos

class InterfaceCapture:
    PROCESS_CAP_BIN = path.Path(
            "/home/cpsc-net-user/repos/physical-testbed-testing/pcap-analysis/src/cap_analysis")
    PROCESS_CAP_OUT_FILE = path.Path(
            "/home/cpsc-net-user/repos/cpsc_of_testbed/rest_client/output.txt")
    CAPTURE_OUTPUT_FILE_PATH = path.Path("/home/cpsc-net-user/capture-files/")

    def __init__(self, iface_name):
        self._iface_name            = iface_name
        self._tcpdump_process       = None

        capture_file_basename       = "cap-file-%d.pcap" % rand.randint(0, 2**32)
        self._capture_file_name     = InterfaceCapture.CAPTURE_OUTPUT_FILE_PATH / capture_file_basename

    def start_capture(self):
        def build_tcpdump_cmd(iface_name):
            capture_file = self._capture_file_name
            tshark_cmd = "tcpdump -i %s -w %s" % (iface_name, capture_file)
            return tshark_cmd.split(" ")

        tcpdump_cmd = build_tcpdump_cmd(self._iface_name)
        if self._tcpdump_process != None:
            raise ValueError("Attempting to start a capture that was already started.")
        self._tcpdump_process = subprocess.Popen(tcpdump_cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def stop_capture(self):
        if self._tcpdump_process == None:
            raise ValueError("Attempting to stop capture that was never started.")
        self._tcpdump_process.terminate()
        self._tcpdump_process = None

    def is_capture_running(self):
        return self._tcpdump_process != None

    def process_capture_data(self):
        def build_cap_analysis_cmd(capture_file_name):
            cap_analysis_cmd = "%s %s" % (InterfaceCapture.PROCESS_CAP_BIN, capture_file_name)
            return cap_analysis_cmd.split(" ")

        cap_analysis_cmd = build_cap_analysis_cmd(self._capture_file_name)
        cap_analysis_proc = subprocess.Popen(cap_analysis_cmd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cap_analysis_proc.wait()
        packets = read_packet_dump_info_from_file(InterfaceCapture.PROCESS_CAP_OUT_FILE)
        return packets
