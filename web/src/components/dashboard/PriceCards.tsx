import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { MarketPrice } from '@/types';
import { cn } from '@/lib/utils';

interface PriceCardsProps {
    prices: Record<string, MarketPrice>;
}

export function PriceCards({ prices }: PriceCardsProps) {
    const cryptoSymbols = ['btcusdt', 'ethusdt', 'solusdt'];

    return (
        <div className="grid grid-cols-3 gap-4 mb-6">
            {cryptoSymbols.map(sym => (
                <MiniPriceCard key={sym} symbol={sym} data={prices[sym]} />
            ))}
        </div>
    );
}

function MiniPriceCard({ symbol, data }: { symbol: string, data?: MarketPrice }) {
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

    const displayName = symbol.substring(0, 3).toUpperCase();

    const formatPrice = (p: number) => {
        return `$${p.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
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
