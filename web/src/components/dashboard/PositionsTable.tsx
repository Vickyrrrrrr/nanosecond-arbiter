import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Position } from '@/types';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

export function PositionsTable({ positions, title = "Active Positions" }: { positions: Record<string, Position>, title?: string }) {
    const positionList = Object.values(positions || {});

    return (
        <Card className="bg-card/50 border-white/5 h-full">
            <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">{title}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Symbol</TableHead>
                            <TableHead>Side</TableHead>
                            <TableHead className="text-right">Entry</TableHead>
                            <TableHead className="text-right">Target</TableHead>
                            <TableHead className="text-right">Stop-Loss</TableHead>
                            <TableHead className="text-right">Market</TableHead>
                            <TableHead className="text-right">Size</TableHead>
                            <TableHead className="text-right">PnL</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        <AnimatePresence>
                            {positionList.filter(p => p && p.symbol).length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
                                        No active positions
                                    </TableCell>
                                </TableRow>
                            ) : (
                                positionList.filter(p => p && p.symbol).map((pos) => {
                                    const currencySymbol = '$';
                                    const displayName = pos.symbol.toUpperCase().replace('USDT', '');

                                    return (
                                        <motion.tr
                                            key={pos.symbol}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            className="border-b border-white/5 hover:bg-white/5"
                                        >
                                            <TableCell className="font-bold whitespace-nowrap">{displayName}</TableCell>
                                            <TableCell>
                                                <span className={cn(
                                                    "px-2 py-1 rounded text-xs font-bold",
                                                    pos.side === 'LONG' ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                                                )}>
                                                    {pos.side}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right font-mono text-muted-foreground">{currencySymbol}{(pos.entry_price || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>

                                            {/* Target Column */}
                                            <TableCell className="text-right font-mono text-green-400/70">
                                                {pos.tp ? `${currencySymbol}${pos.tp.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                                            </TableCell>

                                            {/* Stop-Loss Column */}
                                            <TableCell className="text-right font-mono text-red-400/70">
                                                {pos.sl ? `${currencySymbol}${pos.sl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                                            </TableCell>

                                            <TableCell className="text-right font-mono text-white/90">{currencySymbol}{(pos.current_price || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                                            <TableCell className="text-right font-mono">{pos.quantity}</TableCell>
                                            <TableCell className={cn("text-right font-bold font-mono", (pos.pnl || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                                                {(pos.pnl || 0) >= 0 ? '+' : ''}{currencySymbol}{(pos.pnl || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                <span className="text-xs ml-1 opacity-70">
                                                    ({(pos.pnl_percent || 0).toFixed(2)}%)
                                                </span>
                                            </TableCell>
                                        </motion.tr>
                                    )
                                })
                            )}
                        </AnimatePresence>
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
