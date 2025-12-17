import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TrendingUp, Activity, History, CreditCard, Wallet, Percent } from 'lucide-react';
import { motion } from 'framer-motion';

export interface DashboardPanelProps {
    title: string;
    icon?: React.ReactNode;
    color: 'default' | 'green' | 'blue' | 'purple';
    currency?: 'USD' | 'INR';
    stats: {
        totalPnl: number;
        unrealizedPnl: number;
        balance: number;
        marginUsed: number;
        available: number;
    };
    children?: React.ReactNode;
}

export function DashboardPanel({ title, icon, color, currency = 'USD', stats, children }: DashboardPanelProps) {
    const isProfit = stats.totalPnl >= 0;
    const formatMoney = (val: number) => {
        if (currency === 'INR') {
            return '₹' + val.toLocaleString('en-IN', { maximumFractionDigits: 0 });
        }
        return val.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
    };

    // Derived Colors based on Prop
    const accentColor = color === 'blue' ? 'text-blue-500' : isProfit ? 'text-green-500' : 'text-red-500';
    const accentBg = color === 'blue' ? 'bg-blue-500/10' : isProfit ? 'bg-green-500/10' : 'bg-red-500/10';

    // PnL Value Color should ALWAYS be Green/Red regardless of panel theme
    const pnlColor = isProfit ? 'text-green-500' : 'text-red-500';

    return (
        <Card className="border-white/5 bg-card/40 backdrop-blur-sm overflow-hidden flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b border-white/5 flex items-center gap-3 bg-black/20">
                {icon && <div className={cn("p-1.5 rounded bg-white/5 text-muted-foreground", accentColor)}>{icon}</div>}
                <h3 className="font-bold tracking-tight text-lg">{title}</h3>
            </div>

            {/* Main Content (Chart usually) */}
            <div className="flex-1 p-0 relative min-h-[400px]">
                {children}
            </div>

            {/* P&L / Stats Footer */}
            <div className="p-6 border-t border-white/5 bg-black/10">
                <div className="grid grid-cols-2 gap-8">
                    {/* Left: P&L Summary */}
                    <div>
                        <div className="flex items-center gap-2 mb-2 text-muted-foreground/80">
                            <TrendingUp className="h-3 w-3" />
                            <span className="text-[10px] font-bold uppercase tracking-widest">Total PnL</span>
                        </div>
                        <div className={cn(
                            "text-4xl font-black tracking-tighter tabular-nums",
                            pnlColor
                        )}>
                            {stats.totalPnl >= 0 ? '+' : ''}{formatMoney(stats.totalPnl)}
                        </div>

                        <div className="flex items-center gap-4 mt-3">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-muted-foreground flex items-center gap-1"><Activity size={10} /> Live PnL</span>
                                <span className={cn("font-mono font-bold text-sm", stats.unrealizedPnl >= 0 ? "text-green-400" : "text-red-400")}>
                                    {stats.unrealizedPnl >= 0 ? '+' : ''}{formatMoney(stats.unrealizedPnl)}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Balance Summary */}
                    <div className="flex flex-col justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-1 text-muted-foreground/80">
                                <Wallet className="h-3 w-3" />
                                <span className="text-[10px] font-bold uppercase tracking-widest">Total Balance</span>
                            </div>
                            <div className="text-2xl font-bold tracking-tight">
                                {formatMoney(stats.balance)}
                            </div>
                        </div>

                        <div className="mt-auto">
                            <div className="text-[10px] text-muted-foreground mb-1 uppercase tracking-wider">Available Balance</div>
                            <div className="text-lg font-mono font-semibold text-blue-400">
                                {formatMoney(stats.available)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Card>
    );
}
