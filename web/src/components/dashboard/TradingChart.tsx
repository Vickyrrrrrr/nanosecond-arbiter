import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi, CandlestickSeries } from 'lightweight-charts';
import { useChartData } from '@/hooks/useChartData';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const TIMEFRAMES = [
    { label: '1m', value: '1m' },
    { label: '5m', value: '5m' },
    { label: '15m', value: '15m' },
    { label: '1H', value: '1h' },
    { label: '4H', value: '4h' },
];

export function TradingChart({ symbol }: { symbol: string }) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const [interval, setInterval] = useState('1m'); // Default

    // Pass interval to hook
    const { data, isLoading } = useChartData(symbol, interval);

    // Initialize Chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#d1d5db',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            crosshair: {
                mode: CrosshairMode.Normal,
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
        });

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        chartRef.current = chart;
        seriesRef.current = candlestickSeries;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // Update Data
    useEffect(() => {
        if (!seriesRef.current || data.length === 0) return;
        seriesRef.current.setData(data);

        // Optional: Auto-fit on interval change
        // chartRef.current?.timeScale().fitContent(); 
    }, [data]);

    return (
        <Card className="bg-card/50 border-white/5 overflow-hidden">
            {isLoading && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <Loader2 className="animate-spin" />
                        <span className="text-xs uppercase tracking-widest">Loading Market Data...</span>
                    </div>
                </div>
            )}
            <CardContent className="p-0 relative">
                {/* Header Controls */}
                <div className="absolute top-4 left-4 z-10 flex items-center gap-4">
                    {/* Timeframe Selector */}
                    <div className="flex bg-black/40 backdrop-blur-md rounded-md border border-white/10 p-1 gap-1">
                        {TIMEFRAMES.map(tf => (
                            <button
                                key={tf.value}
                                onClick={() => setInterval(tf.value)}
                                className={cn(
                                    "px-2 py-0.5 text-xs font-medium rounded transition-colors",
                                    interval === tf.value
                                        ? "bg-primary text-primary-foreground"
                                        : "text-muted-foreground hover:bg-white/10 hover:text-foreground"
                                )}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div ref={chartContainerRef} className="w-full h-[400px]" />

            </CardContent>
        </Card>
    );
}
