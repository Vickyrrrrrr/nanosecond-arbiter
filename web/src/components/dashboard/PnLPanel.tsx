import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { TraderState } from '@/types';
import { cn } from '@/lib/utils';
import { TrendingUp, Activity, History } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function usePrevious<T>(value: T): T | undefined {
    const ref = useRef<T>();
    useEffect(() => {
        ref.current = value;
    }, [value]);
    return ref.current;
}

export function PnLPanel({ data, unrealizedPnL }: { data: TraderState | null, unrealizedPnL: number }) {
    const realized = data?.pnl || 0;
    const totalPnl = realized + unrealizedPnL;
    const isProfit = totalPnl >= 0;

    // Previous PnL Logic
    // We want to capture the PREVIOUS unrealized PnL to compare against LIVE
    const prevUnrealized = usePrevious(unrealizedPnL);
    const displayPrev = prevUnrealized !== undefined ? prevUnrealized : unrealizedPnL;

    const formatMoney = (val: number) => val.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

    return (
        <Card className="col-span-1 md:col-span-2 border-white/10 bg-gradient-to-br from-card to-card/50 overflow-hidden relative min-h-[220px]">
            <div className={cn(
                "absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-[100px] rounded-full transition-colors duration-500",
                isProfit ? "bg-green-500/10" : "bg-red-500/10"
            )} />

            <CardContent className="p-6 relative z-10 flex flex-col justify-between h-full">

                {/* SECTION A: TOTAL PnL */}
                <div>
                    <div className="flex items-center gap-2 mb-2 text-muted-foreground/80">
                        <TrendingUp className="h-4 w-4" />
                        <span className="text-xs font-bold uppercase tracking-widest">Total PnL (Realized + Open)</span>
                    </div>
                    <motion.div
                        key={totalPnl}
                        initial={{ opacity: 0.8, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-baseline gap-1"
                    >
                        <span className={cn(
                            "text-5xl font-black tracking-tighter tabular-nums",
                            isProfit ? "text-green-500 drop-shadow-[0_0_10px_rgba(34,197,94,0.2)]" : "text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.2)]"
                        )}>
                            {totalPnl >= 0 ? '+' : ''}{formatMoney(totalPnl)}
                        </span>
                    </motion.div>


                    {/* Breakdown Row */}
                    <div className="flex gap-4 mt-2 text-[10px] font-mono opacity-80">
                        <span className="flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-orange-400"></span>
                            CRYPTO: {((data?.pnl_spot || 0) + (data?.pnl_futures || 0)) >= 0 ? '+' : ''}
                            {formatMoney((data?.pnl_spot || 0) + (data?.pnl_futures || 0))}
                        </span>

                    </div>
                </div>

                {/* SECTION B & C: LIVE vs PREVIOUS */}
                <div className="grid grid-cols-2 gap-4 mt-6 pt-6 border-t border-white/5">

                    {/* LIVE PnL */}
                    <div>
                        <p className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider flex items-center gap-1">
                            <Activity size={10} className="text-blue-400" /> Live PnL (Current)
                        </p>
                        <p className={cn(
                            "text-xl font-bold font-mono flex items-center gap-1",
                            unrealizedPnL >= 0 ? "text-green-400" : "text-red-400"
                        )}>
                            {unrealizedPnL >= 0 ? '+' : ''}{formatMoney(unrealizedPnL)}
                            {/* Small indicator pulse */}
                            <span className="relative flex h-2 w-2 ml-1">
                                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", unrealizedPnL >= 0 ? "bg-green-500" : "bg-red-500")}></span>
                                <span className={cn("relative inline-flex rounded-full h-2 w-2", unrealizedPnL >= 0 ? "bg-green-500" : "bg-red-500")}></span>
                            </span>
                        </p>
                    </div>

                    {/* PREVIOUS PnL */}
                    <div>
                        <p className="text-[10px] text-muted-foreground/50 mb-1 uppercase tracking-wider flex items-center gap-1">
                            <History size={10} /> Previous PnL
                        </p>
                        <p className="text-xl font-bold font-mono text-muted-foreground/60 tabular-nums">
                            {displayPrev >= 0 ? '+' : ''}{formatMoney(displayPrev)}
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card >
    );
}
