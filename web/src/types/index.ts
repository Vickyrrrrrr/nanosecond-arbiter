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
    pnl: number;
    pnl_spot: number;
    pnl_futures: number;
    // New strict sync fields
    margin_spot?: number;
    margin_futures?: number;
    available_spot?: number;
    available_futures?: number;
    positions: Record<string, Position>;
    signal: string;
    confidence: number;
    reasoning: string;
    tradesCount: number;
}

export interface Position {
    entry_price: number;
    current_price: number;
    quantity: number;
    pnl: number;
    pnl_percent: number;
    side: 'LONG' | 'SHORT';
    symbol: string;
}

export const SUPPORTED_PAIRS = ['btcusdt', 'ethusdt', 'solusdt'];
export const API_URL = 'http://localhost:8083/api/ai-decision';
