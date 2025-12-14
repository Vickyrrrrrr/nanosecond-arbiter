'use client';

import React, { useState } from 'react';
import { useBinanceWS } from '@/hooks/useBinanceWS';
import { useTraderData } from '@/hooks/useTraderData';
import { Header } from '@/components/dashboard/Header';
import { PriceCards } from '@/components/dashboard/PriceCards';
import { PnLPanel } from '@/components/dashboard/PnLPanel';
import { AccountSummary } from '@/components/dashboard/AccountSummary';
import { PositionsTable } from '@/components/dashboard/PositionsTable';
import { AiStatus } from '@/components/dashboard/AiStatus';
import { MarketPrice } from '@/types';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const TradingChart = dynamic(
  () => import('@/components/dashboard/TradingChart').then((mod) => mod.TradingChart),
  { ssr: false, loading: () => <div className="h-[400px] bg-muted/20 animate-pulse rounded-xl" /> }
);

export default function DashboardPage() {
  const prices = useBinanceWS();
  const { data: traderData, error } = useTraderData();
  const [selectedSymbol, setSelectedSymbol] = useState('btcusdt');

  const connectionStatus = error ? 'offline' : (traderData ? 'online' : 'connecting');

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
      <Header status={connectionStatus as any} />

      <main className="container mx-auto p-4 md:p-6 space-y-6 max-w-[1600px]">
        {/* Top Row: Prices */}
        <PriceCards prices={prices} />

        {/* Middle Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Left Column: Main Viz (8 cols) */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            {/* Chart Section */}
            <div className="space-y-4">
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
              <TradingChart symbol={selectedSymbol} />
            </div>

            {/* Positions Table */}
            <div className="flex-1 min-h-[300px]">
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
          </div>

          {/* Right Column: Stats (4 cols) - AI REMOVED */}
          <div className="lg:col-span-4 flex flex-col gap-6">
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

            {/* Account Summary consumes full height now */}
            <div className="flex-1">
              <AccountSummary data={traderData} />
            </div>
          </div>
        </div>
      </main>

      {/* Connection Error Toast could go here */}
      {
        error && (
          <div className="fixed bottom-4 right-4 bg-destructive text-destructive-foreground px-4 py-2 rounded shadow-lg animate-in slide-in-from-bottom">
            Warning: Backend Disconnected
          </div>
        )
      }
    </div >
  );
}
