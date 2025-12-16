'use client';

import React, { useState } from 'react';
import { useBinanceWS } from '@/hooks/useBinanceWS';
import { useTraderData } from '@/hooks/useTraderData';
import { Header } from '@/components/dashboard/Header';
import { PriceCards } from '@/components/dashboard/PriceCards';
import { PnLPanel } from '@/components/dashboard/PnLPanel';
import { AccountSummary } from '@/components/dashboard/AccountSummary';
import { PositionsTable } from '@/components/dashboard/PositionsTable';
import ForexMarketSection from '@/components/dashboard/ForexMarketSection';
import { MarketPrice } from '@/types';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const TradingChart = dynamic(
  () => import('@/components/dashboard/TradingChart').then((mod) => mod.TradingChart),
  { ssr: false, loading: () => <div className="h-[400px] bg-muted/20 animate-pulse rounded-xl" /> }
);

export default function DashboardPage() {
  const prices = useBinanceWS();
  const { data: traderData, error, isHealthy } = useTraderData();
  const [selectedSymbol, setSelectedSymbol] = useState('btcusdt');

  // Real connection status based on health check
  const connectionStatus = error ? 'offline' : (isHealthy ? 'online' : 'connecting');

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
      <Header status={connectionStatus as any} />

      <main className="container mx-auto p-4 md:p-6 max-w-[1920px] space-y-6">

        {/* 1. TICKER TAPE (Full Width) */}
        <PriceCards prices={prices} />

        {/* 2. MAIN ROW: CHART + STATS */}
        <div className="flex flex-col lg:flex-row gap-6 items-start">

          {/* LEFT: CHART (Approx 70%) */}
          <div className="flex-[3] w-full min-w-0 flex flex-col gap-4">
            {/* Symbol Selectors */}
            <div className="flex items-center gap-2">
              {['btcusdt', 'ethusdt', 'solusdt'].map(sym => (
                <button
                  key={sym}
                  onClick={() => setSelectedSymbol(sym)}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-bold transition-all",
                    selectedSymbol === sym
                      ? "bg-primary text-primary-foreground shadow-[0_0_15px_rgba(34,197,94,0.4)]"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  )}
                >
                  {sym.toUpperCase()}
                </button>
              ))}
            </div>
            {/* The Chart */}
            <TradingChart symbol={selectedSymbol} />
          </div>

          {/* RIGHT: STATS (Approx 30%) - "Right next to chart" */}
          <div className="flex-1 w-full lg:max-w-[450px] flex flex-col gap-4">
            <PnLPanel
              data={traderData}
              unrealizedPnL={
                Object.values(traderData?.positions || {}).reduce((total, pos) => {
                  const currentPrice = prices[pos.symbol.toLowerCase()]?.price || pos.entry_price;
                  let tradePnl = 0;
                  if (pos.side === 'LONG') {
                    tradePnl = (currentPrice - pos.entry_price) * pos.quantity;
                  } else {
                    tradePnl = (pos.entry_price - currentPrice) * pos.quantity;
                  }
                  return total + tradePnl;
                }, 0)
              }
            />
            <AccountSummary data={traderData} />
          </div>
        </div>

        {/* 3. POSITIONS TABLE (Full Width) */}
        <div className="rounded-xl border border-white/5 bg-card/50 overflow-hidden">
          <div className="p-4 border-b border-white/5 flex items-center gap-2">
            <div className="h-4 w-1 bg-blue-500 rounded-full" />
            <h3 className="font-bold tracking-tight">ACTIVE POSITIONS</h3>
          </div>
          <PositionsTable positions={
            Object.entries(traderData?.positions || {}).reduce((acc, [key, pos]) => {
              const symbolLower = pos.symbol.toLowerCase();
              const currentPrice = prices[symbolLower]?.price || pos.entry_price;

              let pnl = 0;
              if (pos.side === 'LONG') {
                pnl = (currentPrice - pos.entry_price) * pos.quantity;
              } else {
                pnl = (pos.entry_price - currentPrice) * pos.quantity;
              }

              const pnlPercent = (pnl / (pos.entry_price * pos.quantity)) * 100;

              acc[key] = {
                ...pos,
                current_price: currentPrice,
                pnl: pnl,
                pnl_percent: pnlPercent
              };
              return acc;
            }, {} as any)
          } />
        </div>

        {/* 4. GLOBAL MARKETS (Forex/Indices) */}
        <div className="pt-4 border-t border-white/5">
          <ForexMarketSection />
        </div>

      </main>

      {
        error && (
          <div className="fixed bottom-4 right-4 bg-destructive text-destructive-foreground px-4 py-2 rounded shadow-lg animate-in slide-in-from-bottom">
            Warning: Backend Disconnected
          </div>
        )
      }
    </div>
  );
}
