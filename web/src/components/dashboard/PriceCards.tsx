import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { MarketPrice } from '@/types';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PriceCardsProps {
    prices: Record<string, MarketPrice>;
}

export function PriceCards({ prices }: PriceCardsProps) {
    const cryptoSymbols = ['btcusdt', 'ethusdt', 'solusdt'];
    const indianSymbols = ['nifty', 'banknifty'];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* LEFT: CRYPTO SUMMARY (3 Cards) */}
            <div className="grid grid-cols-3 gap-4">
                {cryptoSymbols.map(sym => (
                    <MiniPriceCard key={sym} symbol={sym} data={prices[sym]} type="CRYPTO" />
                ))}
            </div>

            {/* RIGHT: INDIAN INDEX SUMMARY (2 Cards) */}
            <div className="grid grid-cols-2 gap-4">
                {indianSymbols.map(sym => (
                    <MiniPriceCard key={sym} symbol={sym} data={prices[sym]} type="INDIAN" />
                ))}
            </div>
        </div>
    );
}

function MiniPriceCard({ symbol, data, type }: { symbol: string, data?: MarketPrice, type: 'CRYPTO' | 'INDIAN' }) {
    const prevPrice = React.useRef(data?.price);
    const [trend, setTrend] = React.useState<'up' | 'down' | 'neutral'>('neutral');

    React.useEffect(() => {
        if (!data?.price || !prevPrice.current) {
            prevPrice.current = data?.price;
            return;
        }
        if (data.price > prevPrice.current) setTrend('up');
        else if (data.price < prevPrice.current) setTrend('down');
        prevPrice.current = data.price;
        const timeout = setTimeout(() => setTrend('neutral'), 1000);
        return () => clearTimeout(timeout);
    }, [data?.price]);

    const displayName = type === 'CRYPTO'
        ? symbol.substring(0, 3).toUpperCase()
        : symbol.toUpperCase() === 'NIFTY' ? 'NIFTY 50' : symbol.toUpperCase(); // Update Label for Nifty

    const formatPrice = (p: number) => {
        if (type === 'CRYPTO') return `$${p.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        return `₹${p.toLocaleString(undefined, { maximumFractionDigits: 0 })}`; // INR usually no decimals for Index
    };

    return (
        <Card className="bg-card/50 backdrop-blur-sm border-white/5 relative overflow-hidden">
            {/* Background Gradient Pulse */}
            <div className={cn(
                "absolute inset-0 opacity-10 transition-opacity duration-300 pointer-events-none",
                trend === 'up' ? "bg-green-500 opacity-20" : trend === 'down' ? "bg-red-500 opacity-20" : "opacity-0"
            )} />

            <CardContent className="p-4 flex flex-col justify-between h-full">
                <div className="flex justify-between items-start mb-1">
                    <span className="font-bold text-sm text-muted-foreground">{displayName}</span>
                    <div className={cn(
                        "flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded",
                        (data?.change24h || 0) >= 0 ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
                    )}>
                        {(data?.change24h || 0) >= 0 ? '+' : ''}{Math.abs(data?.change24h || 0).toFixed(2)}%
                    </div>
                </div>

                <div className={cn(
                    "text-lg font-mono font-bold tracking-tight transition-colors",
                    trend === 'up' ? "text-green-400" : trend === 'down' ? "text-red-400" : "text-foreground"
                )}>
                    {data?.price ? formatPrice(data.price) : '---'}
                </div>
            </CardContent>
        </Card>
    );
}
