import { useEffect, useState } from 'react';
import { MarketPrice } from '@/types';

export function useForexMarketData() {
    const [prices, setPrices] = useState<Record<string, MarketPrice>>({});
    const [isStale, setIsStale] = useState(false);
    const [lastFetch, setLastFetch] = useState<number>(0);

    useEffect(() => {
        const fetchPrices = async () => {
            try {
                const res = await fetch('http://localhost:8083/api/forex/market-data');
                if (res.ok) {
                    const data = await res.json();
                    setPrices(data);
                    setLastFetch(Date.now());

                    // Check if data is stale (any price older than 10s)
                    const now = Date.now();
                    let stale = false;
                    Object.values(data).forEach((p: any) => {
                        if (p.lastUpdate && (now - p.lastUpdate) > 10000) {
                            stale = true;
                        }
                    });
                    setIsStale(stale);
                }
            } catch (error) {
                console.error("Forex Data Error:", error);
                setIsStale(true);
            }
        };

        // Poll every 1s
        const interval = setInterval(fetchPrices, 1000);
        fetchPrices();

        return () => clearInterval(interval);
    }, []);

    return { prices, isStale, lastFetch };
}
