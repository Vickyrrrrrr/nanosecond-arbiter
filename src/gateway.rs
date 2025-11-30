use std::net::{TcpListener, TcpStream};
use std::io::{BufRead, BufReader, Write};
use std::thread;
use std::sync::{Arc, Mutex};
use crate::matching_engine::{Order, Packet};
use rtrb::Producer;

pub fn run_gateway(producer: Producer<Packet>) -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:8083")?;
    println!("🌐 [GATEWAY] Listening on 127.0.0.1:8083");

    // Wrap producer in Arc<Mutex> to share across threads
    let producer = Arc::new(Mutex::new(producer));

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let producer = producer.clone();
                thread::spawn(move || {
                    handle_client(stream, producer);
                });
            }
            Err(e) => {
                eprintln!("❌ Connection failed: {}", e);
            }
        }
    }
    Ok(())
}

fn handle_client(mut stream: TcpStream, producer: Arc<Mutex<Producer<Packet>>>) {
    let peer_addr = stream.peer_addr().unwrap_or_else(|_| "unknown".parse().unwrap());
    // println!("🔌 New connection from {}", peer_addr); // IO is slow, maybe skip logging

    let reader = BufReader::new(stream.try_clone().expect("Failed to clone stream"));
    let mut lines = reader.lines();

    while let Some(Ok(line)) = lines.next() {
        if line.trim().is_empty() { continue; }

        match serde_json::from_str::<Order>(&line) {
            Ok(order) => {
                let packet = Packet::new(order);
                
                // Push to ring buffer
                let push_result = {
                    let mut p = producer.lock().unwrap();
                    p.push(packet)
                };

                match push_result {
                    Ok(_) => {
                        let _ = stream.write_all(b"{\"status\":\"accepted\"}\n");
                    }
                    Err(_) => {
                        let _ = stream.write_all(b"{\"status\":\"dropped\",\"reason\":\"buffer_full\"}\n");
                    }
                }
            }
            Err(e) => {
                let error_msg = format!("{{\"status\":\"error\",\"reason\":\"{}\"}}\n", e);
                let _ = stream.write_all(error_msg.as_bytes());
            }
        }
    }
}
