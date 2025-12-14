import { useEffect, useState } from 'react';
import { TraderState, API_URL } from '@/types';

export function useTraderData() {
    const [data, setData] = useState<TraderState | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(API_URL);
                if (!res.ok) throw new Error('Failed to fetch trader data');
                const json = await res.json();
                setData(json);
                setError(null);
            } catch (err) {
                // console.error(err); // Squelch logs in production
                setError('Disconnected');
            }
        };

        // Initial fetch
        poll();

        // Poll every 1s
        const interval = setInterval(poll, 1000);
        return () => clearInterval(interval);
    }, []);

    return { data, error };
}
