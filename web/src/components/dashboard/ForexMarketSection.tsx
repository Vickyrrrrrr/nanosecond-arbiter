import { useState, useEffect } from 'react';

// Helper to get latency info
const getLatencyBadge = (symbol: string, lastUpdateMs: number) => {
    const now = Date.now();
    const diffSec = (now - lastUpdateMs) / 1000;

    // Categorize
    const isForex = ["EUR/USD", "GBP/USD", "USD/JPY"].includes(symbol);
    const isUSIndex = ["S&P 500", "Nasdaq 100", "Dow Jones"].includes(symbol);
    const isCommodity = ["XAU/USD (Gold)", "XAG/USD (Silver)", "WTI Crude", "Brent Crude"].includes(symbol);

    // Stale Thresholds
    const staleThreshold = (isForex || isUSIndex) ? 25 : 90;
    const isStale = diffSec > staleThreshold;

    if (isStale) {
        return {
            text: "⚠️ STALE",
            color: "text-red-500",
            border: "border-red-500/50 bg-red-500/10",
            tooltip: `Data stopped updating ${Math.floor(diffSec)}s ago. Check connection.`,
            opacity: "opacity-60"
        };
    }

    if (isForex || isUSIndex) {
        return {
            text: "⚡ LIVE / LOW LATENCY",
            color: "text-green-400",
            border: "border-green-400/50 bg-green-400/10",
            tooltip: "Real-time Snapshot (Yahoo Finance). Updates every ~15s.",
            opacity: "opacity-100"
        };
    }

    if (isCommodity) {
        return {
            text: "⏳ DELAYED 10-30 MIN",
            color: "text-orange-400",
            border: "border-orange-400/50 bg-orange-400/10",
            tooltip: "Exchange-mandated delay for free feed. Not for scalping.",
            opacity: "opacity-100"
        };
    }

    return {
        text: "⏳ DELAYED 15 MIN",
        color: "text-yellow-400",
        border: "border-yellow-400/50 bg-yellow-400/10",
        tooltip: "Standard 15m delay for global indices.",
        opacity: "opacity-100"
    };
};

const PriceCard = ({ symbol, label, data }: { symbol: string, label?: string, data: any }) => {
    const badge = getLatencyBadge(symbol, data?.lastUpdate || 0);

    // Format Price
    const priceVal = data?.price || 0;
    const priceStr = priceVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    const changeVal = parseFloat(data?.change24h || "0");
    const change = changeVal.toFixed(2) + "%";
    const isUp = changeVal >= 0;

    return (
        <div className={`p-3 rounded-lg border border-white/5 bg-card/40 hover:bg-card/60 transition-colors ${badge.opacity} mb-2`}>
            <div className={`flex justify-between items-start mb-2`}>
                <div>
                    <h4 className="font-bold text-sm text-foreground">{label || symbol}</h4>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Yahoo Finance</p>
                </div>

                {/* TOOLTIP BADGE */}
                <div className="group relative">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-mono font-bold cursor-help ${badge.color} ${badge.border}`}>
                        {badge.text}
                    </span>
                    <div className="absolute right-0 w-48 p-2 mt-1 text-[10px] text-slate-200 bg-slate-900 border border-slate-700 rounded opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none">
                        {badge.tooltip}
                    </div>
                </div>
            </div>

            <div className="flex justify-between items-baseline">
                <span className="font-mono text-lg text-slate-100">{priceStr}</span>
                <div className="flex flex-col items-end">
                    <span className={`font-mono text-xs ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                        {isUp ? '▲' : '▼'} {change}
                    </span>
                    <span className="text-[8px] text-slate-500">(vs Prev Close)</span>
                </div>
            </div>

            {/* LAST UPDATE TIME */}
            <div className="mt-1 flex justify-end">
                <span className="text-[8px] text-slate-600 font-mono">
                    Updated: {new Date(data?.lastUpdate || 0).toLocaleTimeString()}
                </span>
            </div>
        </div>
    );
};

export default function ForexMarketSection() {
    const [prices, setPrices] = useState<any>({});

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch('/api/forex/market-data');
                const data = await res.json();
                if (data) setPrices(data);
            } catch (e) {
                // Fallback direct
                try {
                    const res = await fetch('http://localhost:8083/api/forex/market-data');
                    const data = await res.json();
                    if (data) setPrices(data);
                } catch (e2) { }
            }
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    // Column Definitions
    const colForex = [
        { id: 'eurusd', label: 'EUR/USD' },
        { id: 'gbpusd', label: 'GBP/USD' },
        { id: 'usdjpy', label: 'USD/JPY' },
    ];

    const colFxComm = [
        { id: 'xauusd', label: 'XAU/USD (Gold)' },
        { id: 'xagusd', label: 'XAG/USD (Silver)' },
    ];

    const colCoreComm = [
        { id: 'wti', label: 'WTI Crude' },
        { id: 'brent', label: 'Brent Crude' },
    ];

    const colIndices = [
        { id: 'spx', label: 'S&P 500' },
        { id: 'ndx', label: 'Nasdaq 100' },
        { id: 'dji', label: 'Dow Jones' },
        { id: 'gdaxi', label: 'DAX (DE)' },
        { id: 'ftse', label: 'FTSE (UK)' },
        { id: 'ni225', label: 'Nikkei (JP)' },
        { id: 'hsi', label: 'Hang Seng' },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <h2 className="text-lg font-bold flex items-center gap-2">
                    🌍 Global Macro View <span className="text-[10px] bg-purple-600 text-white px-1.5 py-0.5 rounded">YAHOO FINANCE</span>
                </h2>
                <span className="text-xs text-green-400 font-mono">● LIVE POLLING</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

                {/* 1. Forex */}
                <div>
                    <h3 className="text-xs font-bold text-indigo-400 mb-3 uppercase tracking-wider border-b border-indigo-500/20 pb-1">
                        Forex (Major)
                    </h3>
                    <div className="space-y-1">
                        {colForex.map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}
                    </div>
                </div>

                {/* 2. FX Commodities */}
                <div>
                    <h3 className="text-xs font-bold text-yellow-400 mb-3 uppercase tracking-wider border-b border-yellow-500/20 pb-1">
                        FX Commodities
                    </h3>
                    <div className="space-y-1">
                        {colFxComm.map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}
                    </div>
                </div>

                {/* 3. Core Commodities */}
                <div>
                    <h3 className="text-xs font-bold text-orange-400 mb-3 uppercase tracking-wider border-b border-orange-500/20 pb-1">
                        Core Commodities
                    </h3>
                    <div className="space-y-1">
                        {colCoreComm.map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}
                    </div>
                </div>

                {/* 4. Global Indices */}
                <div>
                    <h3 className="text-xs font-bold text-blue-400 mb-3 uppercase tracking-wider border-b border-blue-500/20 pb-1">
                        Global Indices
                    </h3>
                    <div className="space-y-1">
                        {/* US */}
                        <div className="text-[10px] font-bold text-slate-500 mt-1 mb-1">🇺🇸 UNITED STATES</div>
                        {colIndices.slice(0, 3).map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}

                        {/* EU */}
                        <div className="text-[10px] font-bold text-slate-500 mt-3 mb-1">🇪🇺 EUROPE</div>
                        {colIndices.slice(3, 5).map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}

                        {/* ASIA */}
                        <div className="text-[10px] font-bold text-slate-500 mt-3 mb-1">🌏 ASIA / JP</div>
                        {colIndices.slice(5).map(item => (
                            <PriceCard key={item.id} symbol={item.id} label={item.label} data={prices[item.id]} />
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}
