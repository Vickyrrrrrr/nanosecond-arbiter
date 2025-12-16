import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { MarketPrice } from '@/types';
import { ArrowUpRight, ArrowDownRight, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ForexPriceCards({ prices }: { prices: Record<string, MarketPrice> }) {
    // Expected pairs: EURUSD, GBPUSD, USDJPY, XAUUSD
    const pairs = ['eurusd', 'gbpusd', 'usdjpy', 'xauusd'];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {pairs.map(pair => {
                const data = prices[pair] || { price: 0, change24h: 0 };
                const isUp = data.change24h >= 0;

                return (
                    <Card key={pair} className="bg-card/50 border-white/5 backdrop-blur-sm">
                        <CardContent className="p-4">
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400">
                                        <Globe size={16} />
                                    </div>
                                    <span className="font-bold text-sm text-foreground/90 uppercase">{pair}</span>
                                </div>
                                <span className={cn(
                                    "px-2 py-0.5 rounded text-[10px] font-medium flex items-center gap-1",
                                    isUp ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                                )}>
                                    {isUp ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                                    {Math.abs(data.change24h).toFixed(2)}%
                                </span>
                            </div>

                            {/* Price Display */}
                            <div className="space-y-1">
                                <span className={cn(
                                    "text-2xl font-mono font-bold tracking-tight",
                                    isUp ? "text-green-500" : "text-red-500"
                                )}>
                                    {data.price > 0 ? data.price.toFixed(5) : "---"}
                                </span>
                            </div>
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}
