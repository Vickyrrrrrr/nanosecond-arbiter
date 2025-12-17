import { useEffect, useState, useRef } from 'react';
import { MarketPrice, SUPPORTED_PAIRS } from '@/types';

export function useBinanceWS() {
    const [prices, setPrices] = useState<Record<string, MarketPrice>>({});
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Subscribe to ticker streams for 24h change and price
        const streams = SUPPORTED_PAIRS.map(pair => `${pair}@ticker`).join('/');
        const wsUrl = `wss://stream.binance.com:9443/ws/${streams}`;

        const connect = () => {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('Connected to Binance WS');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                // Ticker payload:
                // s: symbol
                // c: last price
                // P: price change percent

                if (data.e === '24hrTicker') {
                    setPrices(prev => ({
                        ...prev,
                        [data.s.toLowerCase()]: {
                            symbol: data.s.toLowerCase(),
                            price: parseFloat(data.c),
                            change24h: parseFloat(data.P),
                            lastUpdate: Date.now()
                        }
                    }));
                }
            };

            ws.onclose = () => {
                console.log('Binance WS closed, reconnecting...');
                setTimeout(connect, 1000);
            };

            ws.onerror = (err) => {
                console.error('Binance WS Error:', err);
                ws.close();
            };
        };

        connect();

        // POLL OTHER MARKETS (FOREX / INDIAN)
        const pollOtherMarkets = async () => {
            try {
                const res = await fetch('/api/forex/market-data');
                const data = await res.json();
                // data format: { "eurusd": { price, change24h, ... }, "nifty": ... }

                setPrices(prev => {
                    const next = { ...prev };
                    for (const [key, val] of Object.entries(data)) {
                        // Cast val to any or MarketPrice
                        next[key] = val as MarketPrice;
                    }
                    return next;
                });
            } catch (e) {
                // Silent fail
            }
        };

        const intervalId = setInterval(pollOtherMarkets, 1000);
        pollOtherMarkets(); // Initial fetch

        return () => {
            clearInterval(intervalId);
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    return prices;
}
