import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { MarketPrice } from '@/types';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface PriceCardsProps {
    prices: Record<string, MarketPrice>;
}

export function PriceCards({ prices }: PriceCardsProps) {
    const symbols = ['btcusdt', 'ethusdt', 'solusdt'];

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {symbols.map(sym => (
                <PriceCard key={sym} symbol={sym} data={prices[sym]} />
            ))}
        </div>
    );
}

function PriceCard({ symbol, data }: { symbol: string, data?: MarketPrice }) {
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

    return (
        <Card className="bg-card/50 backdrop-blur-sm border-white/5 relative overflow-hidden">
            {/* Background Gradient Pulse */}
            <div className={cn(
                "absolute inset-0 opacity-10 transition-opacity duration-500 pointer-events-none",
                trend === 'up' ? "bg-green-500 opacity-20" : trend === 'down' ? "bg-red-500 opacity-20" : "opacity-0"
            )} />

            <CardContent className="p-6 flex justify-between items-center relative z-10">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <div className={cn(
                            "w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs",
                            symbol.startsWith('btc') ? "bg-orange-500/20 text-orange-500" :
                                symbol.startsWith('eth') ? "bg-blue-500/20 text-blue-500" :
                                    "bg-purple-500/20 text-purple-500"
                        )}>
                            {displayName[0]}
                        </div>
                        <span className="font-semibold text-lg text-muted-foreground">{displayName}</span>
                    </div>

                    <div className="flex items-baseline gap-2">
                        <span className={cn(
                            "text-2xl font-mono font-bold tracking-tight transition-colors duration-300",
                            trend === 'up' ? "text-green-400" : trend === 'down' ? "text-red-400" : "text-foreground"
                        )}>
                            ${data?.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '0.00'}
                        </span>
                    </div>
                </div>

                <div className={cn(
                    "flex flex-col items-end",
                    (data?.change24h || 0) >= 0 ? "text-green-500" : "text-red-500"
                )}>
                    <div className="flex items-center gap-1 font-medium bg-black/20 px-2 py-1 rounded">
                        {(data?.change24h || 0) >= 0 ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                        {Math.abs(data?.change24h || 0).toFixed(2)}%
                    </div>
                    <span className="text-xs text-muted-foreground mt-1">24h Change</span>
                </div>
            </CardContent>
        </Card>
    );
}
