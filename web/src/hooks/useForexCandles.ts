import { useEffect, useState, useRef } from 'react';
import { CandlestickData, Time } from 'lightweight-charts';

export function useForexCandles(symbol: string) {
    const [data, setData] = useState<CandlestickData<Time>[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchCandles = async () => {
            if (!symbol) return;
            try {
                // Fetch from our local backend proxy
                // Pass lowercase symbol (eurusd)
                const res = await fetch(`http://localhost:8083/api/forex/candles?symbol=${symbol.toLowerCase()}`);
                if (res.ok) {
                    const raw = await res.json();
                    // Determine if raw data is valid
                    // Backend returns list of dicts: {time, open, high, low, close}
                    // Lightweight charts expects time (unix timestamp), open, high, low, close

                    if (Array.isArray(raw)) {
                        const formatted = raw.map((c: any) => ({
                            // Backend now returns unix timestamp (seconds) or iso string
                            // If number, use directly. If string, parse.
                            time: (typeof c.time === 'number' ? c.time : new Date(c.time).getTime() / 1000) as Time,
                            open: c.open,
                            high: c.high,
                            low: c.low,
                            close: c.close
                        }));
                        // Sort by time just in case
                        formatted.sort((a, b) => (a.time as number) - (b.time as number));
                        setData(formatted);
                    }
                }
            } catch (error) {
                console.error("Forex Candle Error:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchCandles();
        const interval = setInterval(fetchCandles, 5000); // 5s poll for candles

        return () => clearInterval(interval);
    }, [symbol]);

    return { data, isLoading };
}
