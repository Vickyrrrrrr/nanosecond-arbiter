export interface MarketPrice {
    symbol: string;
    price: number;
    change24h: number; // We might need a 24h ticker for this, or just calculate from prev close? 
    // Binance trade stream doesn't give 24h change. 
    // We can use @ticker stream instead of @trade for 24h change.
    // stream: <symbol>@ticker
    lastUpdate: number;
}

export interface TraderState {
    balance: number;
    balance_spot: number;
    balance_futures: number;
    balance_forex: number;
    pnl: number;
    pnl_spot: number;
    pnl_futures: number;
    pnl_forex: number;
    balance_indian?: number;
    pnl_indian?: number;
    // New strict sync fields
    // New strict sync fields
    margin_spot?: number;
    margin_futures?: number;
    available_spot?: number;
    available_futures?: number;
    margin_indian?: number;
    available_indian?: number;
    positions: Record<string, Position>;
    signal: string;
    confidence: number;
    reasoning: string;
    tradesCount: number;

    // LATENCY-SAFE ARCHITECTURE: Data Source & Trading Status
    data_status_crypto?: 'LIVE' | 'DELAYED' | 'OFFLINE';
    data_status_indian?: 'LIVE' | 'OFFLINE' | 'CLOSED';
    trading_enabled_crypto?: boolean;
    trading_enabled_indian?: boolean;
    last_data_update_crypto?: number;
    last_data_update_indian?: number;
    data_warning_crypto?: string;
    data_warning_indian?: string;
    data_source_crypto?: string;
    data_source_indian?: string;
    indian_feed_latency?: number;
}

export interface Position {
    entry_price: number;
    current_price: number;
    quantity: number;
    pnl: number;
    pnl_percent: number;
    side: 'LONG' | 'SHORT';
    symbol: string;
    sl?: number; // Stop Loss
    tp?: number; // Take Profit
}

export const SUPPORTED_PAIRS = ['btcusdt', 'ethusdt', 'solusdt'];
export const API_URL = '/api/ai-decision';
