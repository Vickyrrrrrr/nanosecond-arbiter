use tiny_http::{Server, Request, Response, Header, Method};
use std::sync::{Arc, Mutex};
use std::thread;
use std::fs;
use crate::matching_engine::OrderBook;
use serde_json::json;
use lazy_static::lazy_static;

lazy_static! {
    static ref AI_DECISION: Mutex<String> = Mutex::new(
        r#"{"signal": "NEUTRAL", "reasoning": "Waiting for AI analysis..."}"#.to_string()
    );
    static ref CRYPTO_DECISION: Mutex<String> = Mutex::new(
        r#"{"signals": {"btc": "HOLD", "eth": "HOLD", "sol": "HOLD"}, "reasoning": "Waiting for crypto analysis..."}"#.to_string()
    );
}

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
        
        (Method::Get, "/api/ai-decision") => {
            // Return current AI decision state
            let ai_state = AI_DECISION.lock().unwrap();
            let response = Response::from_string(ai_state.clone())
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            let _ = request.respond(response);
        }
        
        (Method::Post, "/api/ai-decision") => {
            // Store AI decision from Python trader
            let mut content = String::new();
            if request.as_reader().read_to_string(&mut content).is_ok() {
                let mut ai_state = AI_DECISION.lock().unwrap();
                *ai_state = content;
            }
            
            let response = Response::from_string("{\"status\":\"ok\"}")
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            let _ = request.respond(response);
        }
        
        (Method::Get, "/api/crypto-decision") => {
            // Return current crypto decision state
            let crypto_state = CRYPTO_DECISION.lock().unwrap();
            let response = Response::from_string(crypto_state.clone())
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            let _ = request.respond(response);
        }
        
        (Method::Post, "/api/crypto-decision") => {
            // Store crypto decision from Python trader
            let mut content = String::new();
            if request.as_reader().read_to_string(&mut content).is_ok() {
                let mut crypto_state = CRYPTO_DECISION.lock().unwrap();
                *crypto_state = content;
            }
            
            let response = Response::from_string("{\"status\":\"ok\"}")
                .with_header(Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap());
            let _ = request.respond(response);
        }
        
        // Handle CORS preflight
        (Method::Options, _) => {
            let response = Response::from_string("")
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Origin"[..], &b"*"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Methods"[..], &b"GET, POST, OPTIONS"[..]).unwrap())
                .with_header(Header::from_bytes(&b"Access-Control-Allow-Headers"[..], &b"Content-Type"[..]).unwrap());
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
