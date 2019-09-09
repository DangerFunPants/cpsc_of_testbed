
use std::net::*;
use serde::{Serialize, Deserialize};
use serde_json::{Result, Value};
use std::io;
use std::io::{BufRead, Read};
use std::option::Option;

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
    // @TODO: This should be changed to an Ipv4Addr
    dest_addr       : Ipv4Addr,
    // @TODO: This should be changed to an Ipv4Addr
    source_addr     : Ipv4Addr,
    prob_mat        : Vec<f64>,
    tx_rate         : u64,
    variance        : u64,
    // @TODO: This should be an enum type
    traffic_model   : TrafficModel,
    packet_len      : u64,
    src_host        : u64,
    time_slice      : u64,
    tag_value       : Vec<u8>,
    transmit_rates  : Option<Vec<u64>>,
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

fn parse_args(the_json: String) -> Result<FlowParameters> {
    serde_json::from_str(&the_json)
}

fn read_str_from_stdin() -> io::Result<String> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    Ok(input)
}

fn initialize_sockets(flow_parameters: &FlowParams) {

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
}
