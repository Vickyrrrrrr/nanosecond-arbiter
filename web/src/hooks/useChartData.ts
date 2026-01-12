import { useEffect, useState, useRef } from 'react';
import { CandlestickData, Time } from 'lightweight-charts';

export function useChartData(symbol: string, interval: string = '1m') {
    const [data, setData] = useState<CandlestickData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const wsRef = useRef<WebSocket | null>(null);

    // Reset data on change
    useEffect(() => {
        setData([]);
        setIsLoading(true);
    }, [symbol, interval]);

    // Helper to strictly sort and deduplicate data
    const processData = (rawData: any[]): CandlestickData[] => {
        if (!rawData || rawData.length === 0) return [];

        // 1. Sort by time ascending
        const sorted = rawData.sort((a, b) => (a.time as number) - (b.time as number));

        // 2. Deduplicate (keep last occurrence of a timestamp)
        const unique: CandlestickData[] = [];
        let lastTime: number | null = null;

        for (const candle of sorted) {
            const timeVal = candle.time as number;
            if (timeVal !== lastTime) {
                unique.push(candle);
                lastTime = timeVal;
            } else {
                // Replace previous with this one (latest update)
                unique[unique.length - 1] = candle;
            }
        }

        return unique;
    };

    useEffect(() => {
        let isMounted = true;

        const fetchCryptoData = async () => {
            try {
                // Binance API
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

                setData(processData(formatted));
                setIsLoading(false);
                connectBinanceWS();
            } catch (err) {
                console.error("Binance Fetch Error:", err);
                setIsLoading(false);
            }
        };

        const connectBinanceWS = () => {
            if (wsRef.current) wsRef.current.close();
            const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

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
                    let newData = prev;
                    if (prev.length === 0) {
                        newData = [candle];
                    } else {
                        // Optimistically append/update
                        const last = prev[prev.length - 1];
                        if ((last.time as number) === (candle.time as number)) {
                            newData = [...prev.slice(0, -1), candle];
                        } else {
                            newData = [...prev, candle];
                        }
                    }
                    // RE-RUN PROCESS to ensure safety against out-of-order packets
                    return processData(newData);
                });
            };
        };

        fetchCryptoData();

        return () => {
            isMounted = false;
            if (wsRef.current) wsRef.current.close();
        };
    }, [symbol, interval]);

    return { data, isLoading };
}
