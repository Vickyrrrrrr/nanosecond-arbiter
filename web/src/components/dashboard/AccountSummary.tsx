import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { TraderState } from '@/types';
import { Wallet, PieChart, Lock } from 'lucide-react';

export function AccountSummary({ data }: { data: TraderState | null }) {
    const formatMoney = (val: number) => val.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

    return (
        <div className="grid grid-cols-1 gap-4 h-full">
            {/* Total Balance */}
            <Card className="bg-card/50 border-white/5">
                <CardContent className="p-5 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground uppercase mb-1 flex items-center gap-1">
                            <Wallet size={12} /> Total Balance
                        </p>
                        <div className="flex items-baseline gap-2">
                            <p className="text-2xl font-bold font-mono text-foreground">
                                {formatMoney((data?.balance_futures || 0) + (data?.balance_spot || 0))}
                            </p>
                            <span className="text-xs text-muted-foreground">
                                (F: {formatMoney(data?.balance_futures || 0)} + S: {formatMoney(data?.balance_spot || 0)} + 🇮🇳: ₹{(data?.balance_indian || 0).toLocaleString()})
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Margin Used */}
            <Card className="bg-card/50 border-white/5">
                <CardContent className="p-5 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground uppercase mb-1 flex items-center gap-1">
                            <Lock size={12} /> Margin Used
                        </p>
                        <div className="flex items-baseline gap-2">
                            <p className="text-2xl font-bold font-mono text-purple-400">
                                {formatMoney((data?.margin_futures || 0) + (data?.margin_spot || 0))}
                            </p>
                            <span className="text-xs text-muted-foreground">
                                (F: {formatMoney(data?.margin_futures || 0)} + Crypto: {formatMoney(data?.margin_spot || 0)} + 🇮🇳: ₹{(data?.margin_indian || 0).toLocaleString()})
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Available Balance */}
            <Card className="bg-card/50 border-white/5">
                <CardContent className="p-5 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground uppercase mb-1 flex items-center gap-1">
                            <PieChart size={12} /> Available Balance
                        </p>
                        <p className="text-2xl font-bold font-mono text-blue-400">
                            {formatMoney((data?.available_futures || 0) + (data?.available_spot || 0))}
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
