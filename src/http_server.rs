use tiny_http::{Server, Request, Response, Header, Method};
use std::sync::{Arc, Mutex};
use std::thread;
use std::fs;
use crate::matching_engine::OrderBook;
use serde_json::json;

pub fn start_http_server(order_book: Arc<Mutex<OrderBook>>) -> Result<(), Box<dyn std::error::Error>> {
    let server = Server::http("0.0.0.0:8082").unwrap();
    println!("🌐 [HTTP] Server listening on http://0.0.0.0:8082");

    for request in server.incoming_requests() {
        let order_book = order_book.clone();
        thread::spawn(move || {
            handle_request(request, order_book);
        });
    }

    Ok(())
}

fn handle_request(mut request: Request, order_book: Arc<Mutex<OrderBook>>) {
    let url = request.url().to_string();
    
    match (request.method(), url.as_str()) {
        (Method::Get, "/") | (Method::Get, "/index.html") => {
            serve_file(request, "web/index.html", "text/html");
        }
        
        (Method::Get, "/app.js") => {
            serve_file(request, "web/app.js", "application/javascript");
        }
        
        (Method::Get, "/styles.css") => {
            serve_file(request, "web/styles.css", "text/css");
        }
        
        (Method::Get, "/api/orderbook") => {
            let book = order_book.lock().unwrap();
            let json_data = book.to_json();
            
            let response = Response::from_string(json_data)
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            
            let _ = request.respond(response);
        }
        
        (Method::Post, "/api/order") => {
            // Read request body
            let mut content = String::new();
            if let Err(e) = request.as_reader().read_to_string(&mut content) {
                let response = Response::from_string(format!("{{\"status\":\"error\",\"reason\":\"{}\"}}",  e))
                    .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap());
                let _ = request.respond(response);
                return;
            }
            
            match serde_json::from_str::<crate::matching_engine::Order>(&content) {
                Ok(order) => {
                    let mut book = order_book.lock().unwrap();
                    let _executions = book.add_limit_order(order);
                    
                    let response = Response::from_string("{\"status\":\"accepted\"}")
                        .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                        .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
                    
                    let _ = request.respond(response);
                }
                Err(e) => {
                    let response = Response::from_string(format!("{{\"status\":\"error\",\"reason\":\"{}\"}}",  e))
                        .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                        .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
                    let _ = request.respond(response);
                }
            }
        }
        
        (Method::Get, "/api/metrics") => {
            let metrics = json!({
                "latency": 29,
                "throughput": 33543877,
                "uptime": 12345
            });
            
            let response = Response::from_string(metrics.to_string())
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            
            let _ = request.respond(response);
        }
        
        _ => {
            let response = Response::from_string("404 Not Found")
                .with_status_code(404);
            let _ = request.respond(response);
        }
    }
}

fn serve_file(request: Request, path: &str, content_type: &str) {
    match fs::read_to_string(path) {
        Ok(content) => {
            let response = Response::from_string(content)
                .with_header(Header::from_bytes(&b"Content-Type"[..], content_type.as_bytes()).unwrap());
            let _ = request.respond(response);
        }
        Err(_) => {
            let response = Response::from_string("404 Not Found")
                .with_status_code(404);
            let _ = request.respond(response);
        }
    }
}
