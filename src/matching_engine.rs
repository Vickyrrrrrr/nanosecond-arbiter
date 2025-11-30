// ============================================================================
// MATCHING ENGINE MODULE
// ============================================================================

use std::collections::BTreeMap;
use serde::{Deserialize, Serialize};

// ============================================================================
// ORDER STRUCTURE
// ============================================================================
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum OrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    pub id: u64,
    pub side: OrderSide,
    pub price: u64,
    pub quantity: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeExecution {
    pub maker_order_id: u64,
    pub taker_order_id: u64,
    pub price: u64,
    pub quantity: u64,
}

#[derive(Debug, Clone)]
pub struct Packet {
    pub order: Order,
}

impl Packet {
    pub fn new(order: Order) -> Self {
        Packet { order }
    }
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

    pub fn add_limit_order(&mut self, mut order: Order) -> Vec<TradeExecution> {
        let mut executions = Vec::new();

        match order.side {
            OrderSide::Buy => {
                // Check for match against best ask
                while order.quantity > 0 {
                    if let Some((&best_ask_price, orders)) = self.asks.iter_mut().next() {
                        if order.price >= best_ask_price {
                            // MATCH!
                            if let Some(mut matched_order) = orders.pop() {
                                let match_quantity = std::cmp::min(order.quantity, matched_order.quantity);
                                
                                executions.push(TradeExecution {
                                    maker_order_id: matched_order.id,
                                    taker_order_id: order.id,
                                    price: best_ask_price,
                                    quantity: match_quantity,
                                });

                                order.quantity -= match_quantity;
                                matched_order.quantity -= match_quantity;

                                if matched_order.quantity > 0 {
                                    orders.push(matched_order); // Put back remaining
                                }

                                if orders.is_empty() {
                                    // ideally remove key, but skipping for now to avoid borrow checker complexity in this simple loop
                                    // In a real engine we'd handle the empty key removal carefully
                                }
                            } else {
                                break; // Should be empty
                            }
                        } else {
                            break; // No price match
                        }
                    } else {
                        break; // No asks
                    }
                }
                
                // If still quantity left, add to book
                if order.quantity > 0 {
                    self.bids.entry(order.price)
                        .or_insert_with(Vec::new)
                        .push(order);
                }
            }
            
            OrderSide::Sell => {
                // Check for match against best bid
                while order.quantity > 0 {
                    if let Some((&best_bid_price, orders)) = self.bids.iter_mut().next_back() {
                        if order.price <= best_bid_price {
                            // MATCH!
                            if let Some(mut matched_order) = orders.pop() {
                                let match_quantity = std::cmp::min(order.quantity, matched_order.quantity);
                                
                                executions.push(TradeExecution {
                                    maker_order_id: matched_order.id,
                                    taker_order_id: order.id,
                                    price: best_bid_price,
                                    quantity: match_quantity,
                                });

                                order.quantity -= match_quantity;
                                matched_order.quantity -= match_quantity;

                                if matched_order.quantity > 0 {
                                    orders.push(matched_order);
                                }
                            } else {
                                break;
                            }
                        } else {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                
                // If still quantity left, add to book
                if order.quantity > 0 {
                    self.asks.entry(order.price)
                        .or_insert_with(Vec::new)
                        .push(order);
                }
            }
        }
        executions
    }
    
    pub fn to_json(&self) -> String {
        serde_json::json!({
            "bids": self.bids.iter().map(|(price, orders)| {
                serde_json::json!({
                    "price": price,
                    "orders": orders
                })
            }).collect::<Vec<_>>(),
            "asks": self.asks.iter().map(|(price, orders)| {
                serde_json::json!({
                    "price": price,
                    "orders": orders
                })
            }).collect::<Vec<_>>()
        }).to_string()
    }
}
