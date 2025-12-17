import React from 'react';
import { cn } from '@/lib/utils';
import { Activity, Wifi, WifiOff, AlertTriangle, Moon } from 'lucide-react';

interface HeaderProps {
    status?: 'online' | 'offline' | 'connecting';
    dataStatusCrypto?: 'LIVE' | 'DELAYED' | 'OFFLINE';
    dataStatusIndian?: 'LIVE' | 'DELAYED' | 'OFFLINE' | 'CLOSED';
    tradingEnabledCrypto?: boolean;
    tradingEnabledIndian?: boolean;
    dataSourceCrypto?: string;
    dataSourceIndian?: string;
    feedLatencyIndian?: number;
}

export function Header({
    status = 'online',
    dataStatusCrypto = 'LIVE',
    dataStatusIndian = 'DELAYED',
    tradingEnabledCrypto = true,
    tradingEnabledIndian = false,
    dataSourceCrypto = 'EXCHANGE_WS',
    dataSourceIndian = 'YAHOO'
}: HeaderProps) {
    return (
        <header className="flex items-center justify-between border-b border-white/5 bg-background/50 backdrop-blur-md px-6 py-4 sticky top-0 z-50">
            <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Activity className="h-5 w-5 text-primary animate-pulse" />
                </div>
                <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-white/50 bg-clip-text text-transparent">
                    NANOSECOND ARBITER
                </h1>
            </div>

            <div className="flex items-center gap-4">
                {/* Crypto Status */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/30 border border-white/5">
                    <span className="text-[10px] font-bold text-muted-foreground">CRYPTO</span>
                    <div className="h-3 w-px bg-white/10" />
                    <div className={cn(
                        "flex items-center gap-1 text-[10px] font-mono",
                        dataStatusCrypto === 'LIVE' ? "text-green-400" : "text-yellow-400"
                    )}>
                        {dataStatusCrypto === 'LIVE' ? <Wifi size={10} /> : <AlertTriangle size={10} />}
                        {dataStatusCrypto}
                    </div>
                    <div className={cn(
                        "px-1.5 py-0.5 rounded text-[9px] font-bold",
                        tradingEnabledCrypto ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                    )}>
                        {tradingEnabledCrypto ? 'TRADING ON' : 'TRADING OFF'}
                    </div>
                </div>

                {/* Indian Status */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/30 border border-white/5">
                    <span className="text-[10px] font-bold text-muted-foreground">INDIAN</span>
                    <div className="h-3 w-px bg-white/10" />
                    <div className={cn(
                        "flex items-center gap-1 text-[10px] font-mono",
                        dataStatusIndian === 'LIVE' ? "text-green-400" :
                            dataStatusIndian === 'CLOSED' ? "text-slate-400" :
                                dataStatusIndian === 'OFFLINE' ? "text-red-400" : "text-yellow-400"
                    )}>
                        {dataStatusIndian === 'LIVE' ? <Wifi size={10} /> :
                            dataStatusIndian === 'CLOSED' ? <Moon size={10} /> : <WifiOff size={10} />}
                        {dataStatusIndian}
                        {status === 'online' && dataStatusIndian !== 'OFFLINE' && (
                            <span className={cn(
                                "ml-1 text-[9px] px-1 rounded",
                                (dataStatusIndian === 'LIVE' && true) ? "text-green-500 bg-green-950" : "text-red-500 bg-red-950"
                            )}>
                                {/* Placeholder for latency if passed, but for now just Status */}
                            </span>
                        )}
                    </div>
                    {/* LATENCY INDICATOR */}
                    <div className={cn(
                        "text-[9px] font-mono",
                        // Fallback logic if prop not passed
                        "text-muted-foreground"
                    )}>
                        {/* Requires prop update */}
                    </div>
                    <div className={cn(
                        "px-1.5 py-0.5 rounded text-[9px] font-bold",
                        tradingEnabledIndian ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                    )}>
                        {tradingEnabledIndian ? 'TRADING ON' : 'TRADING OFF'}
                    </div>
                </div>

                {/* Connection Status */}
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                    <span className={cn("h-2 w-2 rounded-full",
                        status === 'online' ? "bg-primary shadow-[0_0_8px_rgba(34,197,94,0.5)]" :
                            status === 'connecting' ? "bg-yellow-500 animate-pulse" : "bg-red-500"
                    )} />
                    {status.toUpperCase()}
                </div>
            </div>
        </header>
    );
}
