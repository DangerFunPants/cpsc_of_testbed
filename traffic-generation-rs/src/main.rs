
use std::net::*;
use serde::{Serialize, Deserialize};
use serde_json::{Result, Value};
use std::io;
use std::time;
use std::io::{BufRead, Read};
use std::option::Option;
use std::thread;

#[derive(Serialize, Deserialize, Debug)]
enum TrafficModel {
    Uniform,
    TruncNorm,
    RandomSampling,
    TruncNormSymmetric,
    Gamma,
    Precomputed,
}

#[derive(Serialize, Deserialize, Debug)]
struct FlowParameters {
    dest_port       : u16,
    dest_addr       : Ipv4Addr,
    source_addr     : Ipv4Addr,
    prob_mat        : Vec<f64>,
    tx_rate         : u64,
    variance        : u64,
    traffic_model   : TrafficModel,
    packet_len      : usize,
    src_host        : u64,
    time_slice      : u64,
    tag_value       : Vec<u8>,
    transmit_rates  : Option<Vec<u64>>,
}

#[derive(Serialize, Deserialize, Debug)]
struct FlowParameterList {
    flow_parameters: Vec<FlowParameters>,
}

#[derive(Debug)]
struct FlowTxBlock {
    flow_parameters     : FlowParameters,
    socket              : UdpSocket,
    dest_socket_addr    : SocketAddr,
    data_buffer         : Vec<u8>
}

impl FlowTxBlock {
    pub fn new(flow_parameters: FlowParameters) -> Option<FlowTxBlock> {
        let socket_source_addr = SocketAddr::new(IpAddr::V4(flow_parameters.source_addr), 0);
        match UdpSocket::bind(socket_source_addr) {
            Ok(udp_socket) => {
                let dest_socket_addr = SocketAddr::new(IpAddr::V4(flow_parameters.dest_addr),
                    flow_parameters.dest_port);
                let data_buffer = vec![0; flow_parameters.packet_len];

                Some(FlowTxBlock { flow_parameters      : flow_parameters
                                 , socket               : udp_socket
                                 , dest_socket_addr     : dest_socket_addr
                                 , data_buffer          : data_buffer
                                 })
            },
            Err(_) => None,
        }
    }

    pub fn transmit(self: &Self) -> io::Result<usize> {
        self.socket.send_to(&self.data_buffer, self.dest_socket_addr)
    }
}

fn send_a_udp_packet(destination_addr: Ipv4Addr, port_number: u16) -> io::Result<()> {
    {
        let mut socket = UdpSocket::bind("127.0.0.1:34254")?;
        let buf = [0; 10];
        let destination_addr = SocketAddrV4::new(destination_addr, port_number);

        socket.send_to(&buf, destination_addr)?;
    }
    Ok(())
}

fn parse_args(the_json: String) -> Result<Vec<FlowParameters>> {
    let flow_parameter_list: FlowParameterList = serde_json::from_str(&the_json)?;
    Ok(flow_parameter_list.flow_parameters)
}

fn read_str_from_stdin() -> io::Result<String> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    Ok(input)
}

fn generate_traffic(flow_tx_block: &FlowTxBlock) {
    println!("Generating traffic with FlowTxBlock:\n{:?}", flow_tx_block);
    let packet_burst_size       = flow_tx_block.flow_parameters.packet_len as u64;
    let flow_tx_rate            = flow_tx_block.flow_parameters.tx_rate;
    let burst_tx_duration_ns    = ((packet_burst_size as f64 / flow_tx_rate as f64) * 
                                   10f64.powf(9.0)) as u64;
    println!("burst_tx_duration: {}", burst_tx_duration_ns);

    while true {
        for _ in (0..10) {
            flow_tx_block.transmit();
        }
        thread::sleep(time::Duration::from_nanos(burst_tx_duration_ns));
    }
}

fn main() {
    let input_json = match read_str_from_stdin() {
        Ok(input_json) => input_json,
        Err(stdin_error) => { 
            println!("Failed to read input from standard input. {:?}", stdin_error);
            return
        },
    };

    let flow_params = match parse_args(input_json) {
        Ok(flow_params) => flow_params,
        Err(parse_error) => {
            println!("Failed to parse flow parameters. {:?}", parse_error);
            return
        },
    };
    println!("Flow parameters:\n{:?}", flow_params);

    let mut flow_tx_blocks: Vec<FlowTxBlock> = Vec::new();
    for flow_param in flow_params {
        let flow_tx_block = match FlowTxBlock::new(flow_param) {
            Some(flow_tx_block) => flow_tx_block,
            None => {
                println!("Failed to bind UDP socket to source addr.");
                return
            },
        };
        flow_tx_blocks.push(flow_tx_block);
    }
    println!("FlowTxBlocks:\n{:?}", flow_tx_blocks);
    // let flow_tx_block = FlowTxBlock::new(flow_params);
    // println!("FlowTxBlock\n{:?}", flow_tx_block);
    let mut thread_handles: Vec<thread::JoinHandle<()>> = Vec::new();
    for flow_tx_block in flow_tx_blocks {
        let the_join_handle = thread::spawn(move || generate_traffic(&flow_tx_block));
        thread_handles.push(the_join_handle);
    }

    for thread_handle in thread_handles {
        thread_handle.join();
    }
}
