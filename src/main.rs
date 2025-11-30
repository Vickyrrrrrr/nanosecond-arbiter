// ============================================================================
// LOCK-FREE RING BUFFER - The Nanosecond Arbiter (Phase 2: SPSC Pipeline)
// ============================================================================

mod matching_engine;
use matching_engine::{Order, OrderBook, OrderSide, Packet};
use std::thread;
use std::time::Instant;

// ============================================================================
// PACKET STRUCTURE - The Protocol
// ============================================================================
// Packet moved to matching_engine.rs

// ============================================================================
// MAIN - The SPSC Pipeline Benchmark
// ============================================================================

mod gateway;
mod http_server;
use gateway::run_gateway;
use http_server::start_http_server;
use std::sync::{Arc, Mutex};

// ============================================================================
// MAIN - Production Trading Platform
// ============================================================================

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 NANOSECOND ARBITER - PRODUCTION MODE");
    println!("============================================================\n");
    
    // Configuration
    const RING_BUFFER_CAPACITY: usize = 4096;
    
    println!("📊 Configuration:");
    println!("   • Ring Buffer Capacity: {}", RING_BUFFER_CAPACITY);
    println!("   • Architecture: Web UI + TCP Gateway -> Ring Buffer -> Engine");
    println!();
    
    let (producer, mut consumer) = rtrb::RingBuffer::<Packet>::new(RING_BUFFER_CAPACITY);
    
    // Shared order book for HTTP API access
    let order_book = Arc::new(Mutex::new(OrderBook::new()));
    let order_book_engine = order_book.clone();
    let order_book_http = order_book.clone();
    
    println!("✅ Ring buffer initialized\n");
    
    // ========================================================================
    // THREAD 1: MATCHING ENGINE (Consumer)
    // ========================================================================
    
    thread::spawn(move || {
        println!("⚙️  [ENGINE] Matching engine started on dedicated thread...");
        
        loop {
            match consumer.pop() {
                Ok(packet) => {
                    // Process order and get executions
                    let executions = {
                        let mut book = order_book_engine.lock().unwrap();
                        book.add_limit_order(packet.order)
                    };
                    
                    // Print trade executions
                    for exec in executions {
                        println!("💰 TRADE: {} matched with {} @ {} (Qty: {})", 
                            exec.taker_order_id, exec.maker_order_id, exec.price, exec.quantity);
                    }
                }
                Err(_) => {
                    // Busy wait
                    std::hint::spin_loop();
                }
            }
        }
    });
    
    // ========================================================================
    // THREAD 2: TCP GATEWAY (Producer)
    // ========================================================================
    
    thread::spawn(move || {
        println!("🌐 [GATEWAY] TCP server starting...");
        if let Err(e) = run_gateway(producer) {
            eprintln!("❌ [GATEWAY] Error: {}", e);
        }
    });
    
    // ========================================================================
    // MAIN THREAD: HTTP SERVER + WEB DASHBOARD
    // ========================================================================
    
    println!("🌐 [HTTP] Starting web dashboard...");
    println!("📱 Open http://localhost:8082 in your browser\n");
    
    start_http_server(order_book_http)?;
    
    Ok(())
}

