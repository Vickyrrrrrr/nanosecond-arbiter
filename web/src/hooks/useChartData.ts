import { useEffect, useState, useRef, useCallback } from 'react';
import { CandlestickData, Time } from 'lightweight-charts';

export function useChartData(symbol: string, interval: string = '1m') {
    const [data, setData] = useState<CandlestickData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const wsRef = useRef<WebSocket | null>(null);
    const intervalRef = useRef(interval);

    useEffect(() => {
        intervalRef.current = interval;
    }, [interval]);

    useEffect(() => {
        let isMounted = true;
        setIsLoading(true);
        setData([]); // Clear old data on symbol OR interval switch

        // 1. Fetch History via REST
        const fetchHistory = async () => {
            try {
                // Binance API: interval param
                const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol.toUpperCase()}&interval=${interval}&limit=1000`);
                const klines = await res.json();

                if (!isMounted) return;

                const formatted: CandlestickData[] = klines.map((k: any) => ({
                    time: (k[0] / 1000) as Time,
                    open: parseFloat(k[1]),
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close: parseFloat(k[4]),
                }));

                formatted.sort((a, b) => (a.time as number) - (b.time as number));

                setData(formatted);
                setIsLoading(false);

                connectWebSocket();
            } catch (err) {
                console.error("Failed to fetch chart history:", err);
                setIsLoading(false);
            }
        };

        const connectWebSocket = () => {
            if (wsRef.current) {
                wsRef.current.close();
            }

            // Stream: <symbol>@kline_<interval>
            const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => console.log(`Chart WS Connected: ${symbol} ${interval}`);

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.e !== 'kline') return;

                const k = msg.k;
                const candle: CandlestickData = {
                    time: (k.t / 1000) as Time,
                    open: parseFloat(k.o),
                    high: parseFloat(k.h),
                    low: parseFloat(k.l),
                    close: parseFloat(k.c),
                };

                setData(prev => {
                    if (prev.length === 0) return [candle];
                    const last = prev[prev.length - 1];

                    if ((last.time as number) === (candle.time as number)) {
                        return [...prev.slice(0, -1), candle];
                    } else {
                        return [...prev, candle];
                    }
                });
            };

            ws.onclose = () => console.log(`Chart WS Closed: ${symbol} ${interval}`);
        };

        fetchHistory();

        return () => {
            isMounted = false;
            if (wsRef.current) wsRef.current.close();
        };
    }, [symbol, interval]); // Re-run on interval change

    return { data, isLoading };
}
