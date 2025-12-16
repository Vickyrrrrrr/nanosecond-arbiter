import { useEffect, useState } from 'react';
import { TraderState, API_URL } from '@/types';

export function useTraderData() {
    const [data, setData] = useState<TraderState | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isHealthy, setIsHealthy] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<number>(0);

    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(API_URL);
                if (!res.ok) throw new Error('Failed to fetch trader data');
                const json = await res.json();
                setData(json);
                setError(null);

                // Extract last_update for freshness
                if (json.last_update) {
                    setLastUpdate(json.last_update);
                    const age = Date.now() - json.last_update;
                    setIsHealthy(age < 5000); // Healthy if < 5s old
                } else {
                    setIsHealthy(true); // Assume healthy if no timestamp yet
                }
            } catch (err) {
                setError('Disconnected');
                setIsHealthy(false);
            }
        };

        // Initial fetch
        poll();

        // Poll every 1s
        const interval = setInterval(poll, 1000);
        return () => clearInterval(interval);
    }, []);

    return { data, error, isHealthy, lastUpdate };
}
