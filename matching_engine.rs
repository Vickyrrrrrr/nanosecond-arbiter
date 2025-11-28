// ============================================================================
// MATCHING ENGINE - The Nanosecond Arbiter (Phase 1: Rust Simulation)
// ============================================================================
// This is the core of a High-Frequency Trading exchange that processes orders
// and executes trades with minimal latency.
//
// Author: Portfolio Project - HFT Matching Engine
// Language: Rust (chosen for memory safety + zero-cost abstractions)
// ============================================================================

use std::collections::BTreeMap;

// ============================================================================
// ORDER STRUCTURE
// ============================================================================
/// Represents a single order in the exchange
/// 
/// In real HFT systems, this would be cache-line aligned and packed tightly
/// to minimize memory access latency. For this simulation, we keep it simple.
#[derive(Debug, Clone)]
struct Order {
    id: u64,           // Unique identifier for the order
    side: OrderSide,   // Buy or Sell
    price: u64,        // Price in cents (e.g., 10050 = $100.50) - avoids floating point!
    quantity: u64,     // Number of shares/contracts
}

/// Order side: Buy (Bid) or Sell (Ask)
#[derive(Debug, Clone, Copy, PartialEq)]
enum OrderSide {
    Buy,
    Sell,
}

// ============================================================================
// ORDER BOOK STRUCTURE
// ============================================================================
/// The Order Book maintains all active orders, separated into bids and asks
/// 
/// WHY BTreeMap instead of HashMap or Vec?
/// 
/// 1. **BTreeMap vs HashMap:**
///    - HashMap: O(1) average insert/lookup, BUT keys are UNORDERED
///    - BTreeMap: O(log n) insert/lookup, BUT keys are SORTED
///    - For matching, we NEED the best bid (highest buy price) and best ask 
///      (lowest sell price). BTreeMap keeps prices sorted automatically!
///    - We can get min/max in O(log n) instead of O(n) with HashMap
/// 
/// 2. **BTreeMap vs Vec:**
///    - Vec: Would need manual sorting after each insert = O(n log n)
///    - Vec: Binary search for price levels = O(log n), but insertion = O(n)
///    - BTreeMap: Maintains sorted order with O(log n) insert AND lookup
///    - For high-frequency trading, we insert/remove constantly, so BTreeMap wins
/// 
/// 3. **Time Complexity Summary:**
///    - Insert order: O(log n)
///    - Find best bid/ask: O(log n) - just get first/last key
///    - Remove executed order: O(log n)
/// 
/// In production HFT, we might use custom data structures (like a price-time
/// priority queue with array-based heaps), but BTreeMap is excellent for
/// demonstrating the core matching logic.
struct OrderBook {
    // Bids: Buy orders, sorted by price (descending - highest first)
    // Key = price, Value = Vec of orders at that price level
    bids: BTreeMap<u64, Vec<Order>>,
    
    // Asks: Sell orders, sorted by price (ascending - lowest first)
    // Key = price, Value = Vec of orders at that price level
    asks: BTreeMap<u64, Vec<Order>>,
}

impl OrderBook {
    /// Create a new empty order book
    fn new() -> Self {
        OrderBook {
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
        }
    }

    // ========================================================================
    // CORE MATCHING LOGIC
    // ========================================================================
    /// Add a limit order to the book and attempt to match it
    /// 
    /// Matching Logic:
    /// 1. Check if the order crosses the spread (can execute immediately)
    /// 2. If yes, execute the trade and print confirmation
    /// 3. If no, add the order to the appropriate side of the book
    /// 
    /// A "cross" happens when:
    /// - Buy order price >= lowest Sell price (best ask)
    /// - Sell order price <= highest Buy price (best bid)
    fn add_limit_order(&mut self, order: Order) {
        match order.side {
            OrderSide::Buy => {
                // For a BUY order, check if it can match with the lowest SELL
                // Get the best ask (lowest sell price)
                if let Some((&best_ask_price, _)) = self.asks.iter().next() {
                    // If buy price >= lowest sell price, we have a match!
                    if order.price >= best_ask_price {
                        println!("🔥 TRADE EXECUTED!");
                        println!("   Order ID: {}", order.id);
                        println!("   Side: BUY");
                        println!("   Price: ${}.{:02}", order.price / 100, order.price % 100);
                        println!("   Quantity: {}", order.quantity);
                        println!("   Matched against Ask @ ${}.{:02}", best_ask_price / 100, best_ask_price % 100);
                        println!();
                        
                        // In a real system, we would:
                        // 1. Partially fill if quantities don't match
                        // 2. Remove the matched ask order
                        // 3. Update positions and balances
                        // For this simulation, we just print the execution
                        return;
                    }
                }
                
                // No match found, add to the bid side
                self.bids.entry(order.price)
                    .or_insert_with(Vec::new)
                    .push(order);
            }
            
            OrderSide::Sell => {
                // For a SELL order, check if it can match with the highest BUY
                // Get the best bid (highest buy price)
                if let Some((&best_bid_price, _)) = self.bids.iter().next_back() {
                    // If sell price <= highest buy price, we have a match!
                    if order.price <= best_bid_price {
                        println!("🔥 TRADE EXECUTED!");
                        println!("   Order ID: {}", order.id);
                        println!("   Side: SELL");
                        println!("   Price: ${}.{:02}", order.price / 100, order.price % 100);
                        println!("   Quantity: {}", order.quantity);
                        println!("   Matched against Bid @ ${}.{:02}", best_bid_price / 100, best_bid_price % 100);
                        println!();
                        return;
                    }
                }
                
                // No match found, add to the ask side
                self.asks.entry(order.price)
                    .or_insert_with(Vec::new)
                    .push(order);
            }
        }
    }

    // ========================================================================
    // DISPLAY FUNCTIONS (for debugging and visualization)
    // ========================================================================
    /// Display the current state of the order book
    fn display(&self) {
        println!("📊 ORDER BOOK STATE");
        println!("==========================================");
        
        println!("\n💰 ASKS (Sell Orders - lowest price first):");
        if self.asks.is_empty() {
            println!("   (empty)");
        } else {
            for (price, orders) in self.asks.iter() {
                let total_qty: u64 = orders.iter().map(|o| o.quantity).sum();
                println!("   ${}.{:02} -> {} shares ({} orders)", 
                    price / 100, price % 100, total_qty, orders.len());
            }
        }
        
        println!("\n--- SPREAD ---");
        
        println!("\n💵 BIDS (Buy Orders - highest price first):");
        if self.bids.is_empty() {
            println!("   (empty)");
        } else {
            for (price, orders) in self.bids.iter().rev() {
                let total_qty: u64 = orders.iter().map(|o| o.quantity).sum();
                println!("   ${}.{:02} -> {} shares ({} orders)", 
                    price / 100, price % 100, total_qty, orders.len());
            }
        }
        
        println!("==========================================\n");
    }
}

// ============================================================================
// DRIVER CODE - Simulation Scenario
// ============================================================================
fn main() {
    println!("🚀 MATCHING ENGINE SIMULATION - The Nanosecond Arbiter");
    println!("========================================================\n");
    
    // Create a new order book
    let mut order_book = OrderBook::new();
    
    // ========================================================================
    // SCENARIO: Add 3 Sell orders, then a Buy order that crosses
    // ========================================================================
    
    println!("📝 Step 1: Adding 3 SELL orders to the book...\n");
    
    // Sell order at $100.00
    let sell_order_1 = Order {
        id: 1,
        side: OrderSide::Sell,
        price: 10000,  // $100.00 in cents
        quantity: 100,
    };
    order_book.add_limit_order(sell_order_1);
    println!("   ✅ Added SELL order #1: 100 shares @ $100.00");
    
    // Sell order at $101.00
    let sell_order_2 = Order {
        id: 2,
        side: OrderSide::Sell,
        price: 10100,  // $101.00 in cents
        quantity: 50,
    };
    order_book.add_limit_order(sell_order_2);
    println!("   ✅ Added SELL order #2: 50 shares @ $101.00");
    
    // Sell order at $102.00
    let sell_order_3 = Order {
        id: 3,
        side: OrderSide::Sell,
        price: 10200,  // $102.00 in cents
        quantity: 75,
    };
    order_book.add_limit_order(sell_order_3);
    println!("   ✅ Added SELL order #3: 75 shares @ $102.00\n");
    
    // Display the book before the buy order
    order_book.display();
    
    println!("📝 Step 2: Adding a BUY order at $101.00 (will cross the spread!)...\n");
    
    // Buy order at $101.00 - this will match!
    // Why? Because the buy price ($101) >= lowest sell price ($100)
    let buy_order = Order {
        id: 4,
        side: OrderSide::Buy,
        price: 10100,  // $101.00 in cents
        quantity: 200,
    };
    order_book.add_limit_order(buy_order);
    
    // Display the book after the trade
    println!("📝 Step 3: Order book after the trade:\n");
    order_book.display();
    
    println!("✨ Simulation complete!");
    println!("\n💡 KEY TAKEAWAYS:");
    println!("   • BTreeMap maintains sorted price levels automatically");
    println!("   • O(log n) complexity for insert, lookup, and best price retrieval");
    println!("   • Orders execute immediately when they cross the spread");
    println!("   • In production, we'd handle partial fills and order queues");
}
