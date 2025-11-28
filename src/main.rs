// ============================================================================
// LOCK-FREE RING BUFFER - The Nanosecond Arbiter (Phase 2: SPSC Pipeline)
// ============================================================================
// This implements a Single-Producer Single-Consumer architecture using a
// lock-free ring buffer for zero-latency order processing.
//
// WHY LOCK-FREE?
// - Traditional mutexes add ~25-50ns of overhead per lock/unlock
// - In HFT, we process millions of orders per second
// - Lock-free structures use atomic operations (CPU-level, ~1-5ns)
// - Result: 10-50x lower latency for inter-thread communication
//
// Architecture:
//   [Producer Thread] --push--> [Ring Buffer] --pop--> [Consumer Thread]
//      (Market Data)              (1024 cap)           (Matching Engine)
// ============================================================================

use std::thread;
use std::time::Instant;

// ============================================================================
// ORDER STRUCTURES (from Phase 1)
// ============================================================================

/// Order side: Buy (Bid) or Sell (Ask)
#[derive(Debug, Clone, Copy, PartialEq)]
enum OrderSide {
    Buy,
    Sell,
}

/// Represents a single order in the exchange
#[derive(Debug, Clone)]
struct Order {
    id: u64,
    side: OrderSide,
    price: u64,      // Price in cents to avoid floating point
    quantity: u64,
}

// ============================================================================
// PACKET STRUCTURE - The Protocol
// ============================================================================

/// Packet wraps an Order for transmission through the ring buffer
/// 
/// In production HFT systems, packets would include:
/// - Sequence numbers (for gap detection)
/// - Timestamps (for latency measurement)
/// - Checksums (for data integrity)
/// - Message type discriminators (Order, Cancel, Modify, etc.)
/// 
/// For this simulation, we keep it simple with just the order payload.
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
    println!("🚀 LOCK-FREE RING BUFFER BENCHMARK - The Nanosecond Arbiter");
    println!("============================================================\n");
    
    // Configuration
    const TOTAL_ORDERS: u64 = 1_000_000;
    const RING_BUFFER_CAPACITY: usize = 1024;
    
    println!("📊 Configuration:");
    println!("   • Total Orders: {}", TOTAL_ORDERS.to_string().as_str().chars()
        .collect::<Vec<_>>()
        .chunks(3)
        .rev()
        .map(|c| c.iter().collect::<String>())
        .collect::<Vec<_>>()
        .iter()
        .rev()
        .map(|s| s.as_str())
        .collect::<Vec<_>>()
        .join(","));
    println!("   • Ring Buffer Capacity: {}", RING_BUFFER_CAPACITY);
    println!("   • Architecture: SPSC (Single-Producer Single-Consumer)");
    println!();
    
    // ========================================================================
    // THE HARDWARE: Initialize the lock-free ring buffer
    // ========================================================================
    
    let (mut producer, mut consumer) = rtrb::RingBuffer::<Packet>::new(RING_BUFFER_CAPACITY);
    
    println!("✅ Ring buffer initialized (lock-free, wait-free SPSC queue)\n");
    
    // ========================================================================
    // THREAD 1: THE MARKET (Producer)
    // ========================================================================
    // This thread simulates market data arriving at high speed
    // It pushes orders into the ring buffer as fast as possible
    
    let producer_handle = thread::spawn(move || {
        println!("🏭 [PRODUCER] Market simulator started...");
        
        let mut orders_sent = 0u64;
        let mut spin_count = 0u64;
        
        for i in 0..TOTAL_ORDERS {
            // Create a dummy order
            let order = Order {
                id: i,
                side: if i % 2 == 0 { OrderSide::Buy } else { OrderSide::Sell },
                price: 10000 + (i % 100), // Prices between $100.00 and $101.00
                quantity: 100,
            };
            
            let packet = Packet::new(order);
            
            // Try to push into the ring buffer
            // If buffer is full, spin-wait (this is the "backpressure" mechanism)
            loop {
                match producer.push(packet.clone()) {
                    Ok(_) => {
                        orders_sent += 1;
                        break;
                    }
                    Err(_) => {
                        // Buffer is full! Yield to the consumer thread
                        // In production, you might use more sophisticated backpressure
                        spin_count += 1;
                        thread::yield_now();
                    }
                }
            }
        }
        
        println!("🏭 [PRODUCER] Finished sending {} orders", orders_sent);
        if spin_count > 0 {
            println!("🏭 [PRODUCER] Had to spin-wait {} times (buffer was full)", spin_count);
        }
    });
    
    // ========================================================================
    // THREAD 2: THE ENGINE (Consumer)
    // ========================================================================
    // This thread processes orders from the ring buffer
    // It's the "matching engine" that would execute trades
    
    let consumer_handle = thread::spawn(move || {
        println!("⚙️  [CONSUMER] Matching engine started...");
        
        let mut orders_processed = 0u64;
        let start_time = Instant::now();
        
        // Process until we've received all orders
        while orders_processed < TOTAL_ORDERS {
            // Try to pop a packet from the ring buffer
            match consumer.pop() {
                Ok(packet) => {
                    // Got an order! Process it
                    // In a real system, this would:
                    // 1. Validate the order
                    // 2. Check risk limits
                    // 3. Match against the order book
                    // 4. Execute trades
                    // 5. Send confirmations
                    
                    // For this benchmark, we just count it
                    orders_processed += 1;
                    
                    // Optional: Print progress every 100k orders
                    if orders_processed % 100_000 == 0 {
                        println!("⚙️  [CONSUMER] Processed {} orders...", orders_processed);
                    }
                }
                Err(_) => {
                    // Buffer is empty, keep checking
                    // This is a busy-wait loop (common in HFT for minimal latency)
                    // In production, you might use a hybrid approach with occasional yields
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
    
    // Wait for producer to finish
    producer_handle.join().expect("Producer thread panicked");
    
    // Wait for consumer to finish and get results
    let (orders_processed, elapsed) = consumer_handle.join().expect("Consumer thread panicked");
    
    // ========================================================================
    // PERFORMANCE METRICS
    // ========================================================================
    
    println!("\n🎯 BENCHMARK RESULTS");
    println!("============================================================");
    
    let elapsed_secs = elapsed.as_secs_f64();
    let elapsed_nanos = elapsed.as_nanos();
    
    // Throughput: orders per second
    let throughput = orders_processed as f64 / elapsed_secs;
    
    // Latency: nanoseconds per order (average)
    let latency_per_order = elapsed_nanos / orders_processed as u128;
    
    println!("📦 Orders Processed: {}", orders_processed);
    println!("⏱️  Total Time: {:.3} seconds", elapsed_secs);
    println!("🚀 Throughput: {:.0} orders/second", throughput);
    println!("⚡ Latency per Order: {} ns", latency_per_order);
    println!();
    
    // ========================================================================
    // ANALYSIS & INSIGHTS
    // ========================================================================
    
    println!("💡 PERFORMANCE INSIGHTS:");
    
    if throughput > 10_000_000.0 {
        println!("   🏆 EXCELLENT: >10M orders/sec - Production-grade HFT performance!");
    } else if throughput > 1_000_000.0 {
        println!("   ✅ GOOD: >1M orders/sec - Suitable for most trading applications");
    } else {
        println!("   ⚠️  NEEDS OPTIMIZATION: <1M orders/sec");
    }
    
    if latency_per_order < 100 {
        println!("   ⚡ Ultra-low latency: <100ns per order");
    } else if latency_per_order < 1000 {
        println!("   ⚡ Low latency: <1μs per order");
    }
    
    println!();
    println!("🔬 WHY IS THIS FAST?");
    println!("   • Lock-free: No mutex overhead (~25-50ns saved per operation)");
    println!("   • Wait-free: Consumer never blocks on locks");
    println!("   • Cache-friendly: Ring buffer keeps data in CPU cache");
    println!("   • Zero-copy: Orders passed by value (no heap allocations)");
    println!();
    
    println!("🎓 NEXT STEPS FOR PORTFOLIO:");
    println!("   1. Add latency histograms (p50, p99, p99.9)");
    println!("   2. Implement multiple consumers (SPMC pattern)");
    println!("   3. Add CPU pinning (thread affinity)");
    println!("   4. Measure cache misses with perf tools");
    println!("   5. Compare against mutex-based queue");
}
