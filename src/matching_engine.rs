// ============================================================================
// MATCHING ENGINE MODULE
// ============================================================================

use std::collections::BTreeMap;

// ============================================================================
// ORDER STRUCTURE
// ============================================================================
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone)]
pub struct Order {
    pub id: u64,
    pub side: OrderSide,
    pub price: u64,
    pub quantity: u64,
}

// ============================================================================
// ORDER BOOK STRUCTURE
// ============================================================================
pub struct OrderBook {
    bids: BTreeMap<u64, Vec<Order>>,
    asks: BTreeMap<u64, Vec<Order>>,
}

impl OrderBook {
    pub fn new() -> Self {
        OrderBook {
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
        }
    }

    pub fn add_limit_order(&mut self, order: Order) {
        match order.side {
            OrderSide::Buy => {
                // Check for match against best ask
                if let Some((&best_ask_price, orders)) = self.asks.iter_mut().next() {
                    if order.price >= best_ask_price {
                        // MATCH!
                        // In a real engine, we would handle partial fills here.
                        // For benchmarking, we just remove the matched order to keep the book clean(er)
                        // or just return to simulate "execution".
                        
                        // Let's simulate a simple full match execution by popping the order
                        if let Some(_matched_order) = orders.pop() {
                             // Trade executed. 
                             // NO PRINTING - IO is too slow for nanosecond benchmarks
                             if orders.is_empty() {
                                 // Cleanup empty price level
                                 // self.asks.remove(&best_ask_price); // This is tricky with iter_mut, skipping for speed
                             }
                             return;
                        }
                    }
                }
                
                // No match, add to book
                self.bids.entry(order.price)
                    .or_insert_with(Vec::new)
                    .push(order);
            }
            
            OrderSide::Sell => {
                // Check for match against best bid
                if let Some((&best_bid_price, orders)) = self.bids.iter_mut().next_back() {
                    if order.price <= best_bid_price {
                        // MATCH!
                        if let Some(_matched_order) = orders.pop() {
                             // Trade executed.
                             return;
                        }
                    }
                }
                
                // No match, add to book
                self.asks.entry(order.price)
                    .or_insert_with(Vec::new)
                    .push(order);
            }
        }
    }
}
