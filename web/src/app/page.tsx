'use client';

import React, { useState } from 'react';
import { useBinanceWS } from '@/hooks/useBinanceWS';
import { useTraderData } from '@/hooks/useTraderData';
import { Header } from '@/components/dashboard/Header';
import { PriceCards } from '@/components/dashboard/PriceCards';
import { DashboardPanel } from '@/components/dashboard/DashboardPanel';
import { PositionsTable } from '@/components/dashboard/PositionsTable';

import { cn } from '@/lib/utils';
import { Zap, Globe } from 'lucide-react';
import dynamic from 'next/dynamic';

const TradingChart = dynamic(
  () => import('@/components/dashboard/TradingChart').then((mod) => mod.TradingChart),
  { ssr: false, loading: () => <div className="h-[400px] bg-muted/20 animate-pulse rounded-xl" /> }
);

export default function DashboardPage() {
  const prices = useBinanceWS();
  const { data: traderData, error, isHealthy } = useTraderData();
  const [selectedSymbol, setSelectedSymbol] = useState('btcusdt');
  const [selectedIndianSymbol, setSelectedIndianSymbol] = useState('NIFTY');

  // Real connection status
  const connectionStatus = error ? 'offline' : (isHealthy ? 'online' : 'connecting');

  // === CRYPTO STATS ===
  const cryptoStats = {
    totalPnl: (traderData?.pnl_futures || 0) + (traderData?.pnl_spot || 0), // CLOSED ONLY
    unrealizedPnl: Object.values(traderData?.positions || {}).reduce((total, pos) => {
      const sym = pos.symbol.toLowerCase();
      if (sym === 'nifty' || sym === 'banknifty') return total;

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

  // === INDIAN STATS ===
  const indianStats = {
    totalPnl: traderData?.pnl_indian || 0, // CLOSED ONLY
    unrealizedPnl: Object.values(traderData?.positions || {}).reduce((total, pos) => {
      const sym = pos.symbol.toUpperCase(); // Ensure standard case
      if (sym !== 'NIFTY' && sym !== 'BANKNIFTY') return total;

      // Backend sends live PnL in the position object
      return total + (pos.pnl || 0);
    }, 0),
    balance: traderData?.balance_indian || 0,
    marginUsed: 0, // REMOVED
    available: traderData?.available_indian || traderData?.balance_indian || 0
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 pb-20">
      <Header
        status={connectionStatus as any}
        dataStatusCrypto={traderData?.data_status_crypto || 'LIVE'}
        dataStatusIndian={traderData?.data_status_indian || 'OFFLINE'}
        tradingEnabledCrypto={traderData?.trading_enabled_crypto ?? true}
        tradingEnabledIndian={traderData?.trading_enabled_indian ?? false}
        dataSourceCrypto={traderData?.data_source_crypto || 'EXCHANGE_WS'}
        dataSourceIndian={traderData?.data_source_indian || 'DISCONNECTED'}
        feedLatencyIndian={traderData?.indian_feed_latency}
      />

      <main className="container mx-auto p-4 md:p-6 max-w-[1920px] space-y-6">

        {/* 1. TICKER ROW (Split) */}
        <PriceCards prices={prices} />

        {/* 2. MAIN DASHBOARDS (Split 50/50) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start h-full">

          {/* LEFT: CRYPTO DASHBOARD */}
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

          {/* RIGHT: INDIAN MARKET DASHBOARD */}
          <DashboardPanel
            title="INDIAN MARKET"
            icon={<Globe size={18} />}
            color="blue"
            currency="INR"
            stats={indianStats}
          >
            <div className="absolute top-4 right-20 z-20 flex gap-2">
              {['NIFTY', 'BANKNIFTY'].map(sym => (
                <button
                  key={sym}
                  onClick={() => setSelectedIndianSymbol(sym)}
                  className={cn(
                    "px-3 py-1 rounded text-xs font-bold transition-all uppercase",
                    selectedIndianSymbol === sym
                      ? "bg-blue-500 text-white"
                      : "bg-black/40 text-muted-foreground hover:bg-white/10"
                  )}
                >
                  {sym === 'NIFTY' ? 'NIFTY 50' : sym}
                </button>
              ))}
            </div>
            {/* TradingChart handles fetching history for chart */}
            <TradingChart symbol={selectedIndianSymbol} marketType="INDIAN" />
          </DashboardPanel>
        </div>

        {/* 3. SPLIT POSITIONS TABLES */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          {/* Crypto Positions */}
          <PositionsTable
            title="Active Crypto Positions"
            positions={
              Object.entries(traderData?.positions || {}).reduce((acc, [key, pos]) => {
                const sym = pos.symbol.toUpperCase();
                if (["NIFTY", "BANKNIFTY"].includes(sym)) return acc;

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

          {/* Indian Positions */}
          <PositionsTable
            title="Active Indian Positions"
            positions={
              Object.entries(traderData?.positions || {}).reduce((acc, [key, pos]) => {
                const sym = pos.symbol.toUpperCase();
                // Only keep NIFTY and BANKNIFTY for Indian positions
                if (!["NIFTY", "BANKNIFTY"].includes(sym)) return acc;

                // Backend already provides live PnL for Indian markets (from IndianFOTrader.check_exit)
                // Use backend PnL if available, else 0 (fallback)
                // Also pass SL/TP
                const pnl = pos.pnl || 0;
                const pnlPercent = (pos.quantity && pos.entry_price) ? (pnl / (pos.entry_price * pos.quantity)) * 100 : 0;

                // For Price, use backend provided current_price logic or entry if missing, 
                // but really the backend should send current_price or we rely on the pnl
                // The position object from backend DOES NOT include 'current_price' explicitly in update_dashboard
                // but it helps calculate PnL. We can back-calculate or leave as entry if strictly PnL based.
                // However, user wants "Market" column.
                // Since we don't have Indian market data in 'prices' (Binance), we might need to rely on what backend sent.
                // Backend sends: entry, qty, sl, tp, pnl.
                // CURRENT PRICE = entry + (pnl/qty) [for LONG]
                // CURRENT PRICE = entry - (pnl/qty) [for SHORT]

                let calculatedMarketPrice = pos.entry_price;
                if (pos.quantity > 0) {
                  if (pos.side === 'LONG') {
                    calculatedMarketPrice = pos.entry_price + (pnl / pos.quantity);
                  } else {
                    calculatedMarketPrice = pos.entry_price - (pnl / pos.quantity);
                  }
                }

                acc[key] = {
                  ...pos,
                  current_price: calculatedMarketPrice,
                  pnl: pnl,
                  pnl_percent: pnlPercent,
                  tp: pos.tp,
                  sl: pos.sl
                };
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
