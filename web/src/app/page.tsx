'use client';

import React, { useState } from 'react';
import { useBinanceWS } from '@/hooks/useBinanceWS';
import { useTraderData } from '@/hooks/useTraderData';
import { Header } from '@/components/dashboard/Header';
import { PriceCards } from '@/components/dashboard/PriceCards';
import { DashboardPanel } from '@/components/dashboard/DashboardPanel';
import { PositionsTable } from '@/components/dashboard/PositionsTable';

import { cn } from '@/lib/utils';
import { Zap } from 'lucide-react';
import dynamic from 'next/dynamic';

const TradingChart = dynamic(
  () => import('@/components/dashboard/TradingChart').then((mod) => mod.TradingChart),
  { ssr: false, loading: () => <div className="h-[400px] bg-muted/20 animate-pulse rounded-xl" /> }
);

export default function DashboardPage() {
  const prices = useBinanceWS();
  const { data: traderData, error, isHealthy } = useTraderData();
  const [selectedSymbol, setSelectedSymbol] = useState('btcusdt');

  // Real connection status
  const connectionStatus = error ? 'offline' : (isHealthy ? 'online' : 'connecting');

  // === CRYPTO STATS ===
  const cryptoStats = {
    totalPnl: (traderData?.pnl_futures || 0) + (traderData?.pnl_spot || 0), // CLOSED ONLY
    unrealizedPnl: Object.values(traderData?.positions || {}).reduce((total, pos) => {
      const sym = pos.symbol.toLowerCase();
      const currentPrice = prices[sym]?.price || pos.entry_price;
      let tradePnl = 0;
      if (pos.side === 'LONG') tradePnl = (currentPrice - pos.entry_price) * pos.quantity;
      else tradePnl = (pos.entry_price - currentPrice) * pos.quantity;
      return total + tradePnl;
    }, 0),
    balance: (traderData?.balance_futures || 0) + (traderData?.balance_spot || 0),
    marginUsed: 0, // REMOVED
    available: (traderData?.available_futures || 0) + (traderData?.balance_spot || 0)
  };



  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 pb-20">
      <Header
        status={connectionStatus as any}
        dataStatusCrypto={traderData?.data_status_crypto || 'LIVE'}
        tradingEnabledCrypto={traderData?.trading_enabled_crypto ?? true}
        dataSourceCrypto={traderData?.data_source_crypto || 'EXCHANGE_WS'}
      />

      <main className="container mx-auto p-4 md:p-6 max-w-[1920px] space-y-6">

        {/* 1. TICKER ROW (Split) */}
        <PriceCards prices={prices} />

        {/* MAIN DASHBOARD */}
        <div className="w-full">
          <DashboardPanel
            title="CRYPTO PERPETUALS"
            icon={<Zap size={18} />}
            color="default"
            stats={cryptoStats}
          >
            {/* Symbol Selectors Overlay or Pre-Chart */}
            <div className="absolute top-4 right-20 z-20 flex gap-2">
              {['btcusdt', 'ethusdt', 'solusdt'].map(sym => (
                <button
                  key={sym}
                  onClick={() => setSelectedSymbol(sym)}
                  className={cn(
                    "px-3 py-1 rounded text-xs font-bold transition-all uppercase",
                    selectedSymbol === sym
                      ? "bg-primary text-black"
                      : "bg-black/40 text-muted-foreground hover:bg-white/10"
                  )}
                >
                  {sym.replace('usdt', '')}
                </button>
              ))}
            </div>
            <TradingChart symbol={selectedSymbol} />
          </DashboardPanel>
        </div>

        {/* POSITIONS TABLE */}
        <div className="mt-8">
          <PositionsTable
            title="Active Crypto Positions"
            positions={
              Object.entries(traderData?.positions || {}).reduce((acc, [key, pos]) => {
                const symbolLower = pos.symbol.toLowerCase();
                const currentPrice = prices[symbolLower]?.price || pos.entry_price;
                let pnl = 0;
                if (pos.side === 'LONG') pnl = (currentPrice - pos.entry_price) * pos.quantity;
                else pnl = (pos.entry_price - currentPrice) * pos.quantity;
                const pnlPercent = (pnl / (pos.entry_price * pos.quantity)) * 100;

                acc[key] = { ...pos, current_price: currentPrice, pnl, pnl_percent: pnlPercent, tp: pos.tp, sl: pos.sl };
                return acc;
              }, {} as any)
            }
          />
        </div>

      </main>

      {error && (
        <div className="fixed bottom-4 right-4 bg-destructive text-destructive-foreground px-4 py-2 rounded shadow-lg animate-in slide-in-from-bottom">
          Disconnected from Trading Core
        </div>
      )}
    </div>
  );
}
