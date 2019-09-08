
use std::net::*;

fn send_a_udp_packet(destination_addr: Ipv4Addr, port_number: u16) -> std::io::Result<()> {
    {
        let mut socket = UdpSocket::bind("127.0.0.1:34254")?;
        let buf = [0; 10];
        let destination_addr = SocketAddrV4::new(destination_addr, port_number);

        socket.send_to(buf, destination_addr)?;
    }
    Ok(())
}

fn main() {
    let destination_addr = Ipv4Addr::new(127, 0, 0, 1);
    let destination_port_number = 50000;
    let result = send_a_udp_packet(destination_addr, destination_port_number);
    println!("Hello, world!");
    println!("Attempted to send some data.")
}
