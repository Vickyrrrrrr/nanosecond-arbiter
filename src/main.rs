// ============================================================================
// LOCK-FREE RING BUFFER - The Nanosecond Arbiter (Phase 2: SPSC Pipeline)
// ============================================================================

mod matching_engine;
use matching_engine::{Order, OrderBook, OrderSide};
use std::thread;
use std::time::Instant;

// ============================================================================
// PACKET STRUCTURE - The Protocol
// ============================================================================

#[derive(Debug, Clone)]
struct Packet {
    order: Order,
}

impl Packet {
    fn new(order: Order) -> Self {
        Packet { order }
    }
}

// ============================================================================
// MAIN - The SPSC Pipeline Benchmark
// ============================================================================

fn main() {
    println!("🚀 LOCK-FREE RING BUFFER + MATCHING ENGINE BENCHMARK");
    println!("============================================================\n");
    
    // Configuration
    const TOTAL_ORDERS: u64 = 1_000_000;
    const RING_BUFFER_CAPACITY: usize = 1024;
    
    println!("📊 Configuration:");
    println!("   • Total Orders: 1,000,000");
    println!("   • Ring Buffer Capacity: {}", RING_BUFFER_CAPACITY);
    println!("   • Architecture: SPSC (Single-Producer Single-Consumer)");
    println!("   • Logic: FULL OrderBook Execution (BTreeMap Insert/Match)");
    println!();
    
    let (mut producer, mut consumer) = rtrb::RingBuffer::<Packet>::new(RING_BUFFER_CAPACITY);
    
    println!("✅ Ring buffer initialized\n");
    
    // ========================================================================
    // THREAD 1: THE MARKET (Producer)
    // ========================================================================
    
    let producer_handle = thread::spawn(move || {
        println!("🏭 [PRODUCER] Market simulator started...");
        
        let mut orders_sent = 0u64;
        
        for i in 0..TOTAL_ORDERS {
            // Create a dummy order
            // We alternate buy/sell to create matches and keep the book size manageable
            let side = if i % 2 == 0 { OrderSide::Buy } else { OrderSide::Sell };
            // Price oscillates to create matches
            let price = 10000 + (i % 10); 
            
            let order = Order {
                id: i,
                side,
                price, 
                quantity: 100,
            };
            
            let packet = Packet::new(order);
            
            loop {
                match producer.push(packet.clone()) {
                    Ok(_) => {
                        orders_sent += 1;
                        break;
                    }
                    Err(_) => {
                        thread::yield_now();
                    }
                }
            }
        }
        println!("🏭 [PRODUCER] Finished sending {} orders", orders_sent);
    });
    
    // ========================================================================
    // THREAD 2: THE ENGINE (Consumer)
    // ========================================================================
    
    let consumer_handle = thread::spawn(move || {
        println!("⚙️  [CONSUMER] Matching engine started...");
        
        // Initialize the ACTUAL OrderBook
        let mut order_book = OrderBook::new();
        
        let mut orders_processed = 0u64;
        let start_time = Instant::now();
        
        while orders_processed < TOTAL_ORDERS {
            match consumer.pop() {
                Ok(packet) => {
                    // ACTUALLY PROCESS THE ORDER
                    order_book.add_limit_order(packet.order);
                    
                    orders_processed += 1;
                    
                    if orders_processed % 100_000 == 0 {
                        println!("⚙️  [CONSUMER] Processed {} orders...", orders_processed);
                    }
                }
                Err(_) => {
                    thread::yield_now();
                }
            }
        }
        
        let elapsed = start_time.elapsed();
        println!("⚙️  [CONSUMER] Finished processing {} orders", orders_processed);
        (orders_processed, elapsed)
    });
    
    // ========================================================================
    // WAIT FOR COMPLETION & CALCULATE METRICS
    // ========================================================================
    
    println!("\n⏳ Processing orders...\n");
    
    producer_handle.join().expect("Producer thread panicked");
    let (orders_processed, elapsed) = consumer_handle.join().expect("Consumer thread panicked");
    
    println!("\n🎯 BENCHMARK RESULTS (WITH LOGIC)");
    println!("============================================================");
    
    let elapsed_secs = elapsed.as_secs_f64();
    let elapsed_nanos = elapsed.as_nanos();
    let throughput = orders_processed as f64 / elapsed_secs;
    let latency_per_order = elapsed_nanos / orders_processed as u128;
    
    println!("📦 Orders Processed: {}", orders_processed);
    println!("⏱️  Total Time: {:.3} seconds", elapsed_secs);
    println!("🚀 Throughput: {:.0} orders/second", throughput);
    println!("⚡ Latency per Order: {} ns", latency_per_order);
    println!();
}

