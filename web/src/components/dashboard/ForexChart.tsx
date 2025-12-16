import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi, CandlestickSeries } from 'lightweight-charts';
import { useForexCandles } from '@/hooks/useForexCandles';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ForexChart({ symbol }: { symbol: string }) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    const { data, isLoading } = useForexCandles(symbol);

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
            height: 300, // Slightly shorter for sidebar
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
            upColor: '#3b82f6', // Blue for Forex Bull
            downColor: '#ef4444',
            borderVisible: false,
            wickUpColor: '#3b82f6',
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
        // chartRef.current?.timeScale().fitContent();
    }, [data]);

    return (
        <Card className="bg-card/50 border-white/5 overflow-hidden">
            {/* Header Overlay */}
            <div className="absolute top-2 left-4 z-10 flex items-center gap-2">
                <span className="text-xs font-bold text-muted-foreground uppercase">{symbol} CHART (5M)</span>
            </div>

            {isLoading && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <Loader2 className="animate-spin text-blue-400" />
                </div>
            )}
            <CardContent className="p-0 relative">
                <div ref={chartContainerRef} className="w-full h-[300px]" />
            </CardContent>
        </Card>
    );
}
