import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Position } from '@/types';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

export function PositionsTable({ positions }: { positions: Record<string, Position> }) {
    const positionList = Object.values(positions || {});

    return (
        <Card className="bg-card/50 border-white/5 h-full">
            <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Active Positions</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Symbol</TableHead>
                            <TableHead>Side</TableHead>
                            <TableHead className="text-right">Entry</TableHead>
                            <TableHead className="text-right">Market</TableHead>
                            <TableHead className="text-right">Size</TableHead>
                            <TableHead className="text-right">PnL</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        <AnimatePresence>
                            {positionList.filter(p => p && p.symbol).length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                                        No active positions
                                    </TableCell>
                                </TableRow>
                            ) : (
                                positionList.filter(p => p && p.symbol).map((pos) => (
                                    <motion.tr
                                        key={pos.symbol}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        className="border-b border-white/5 hover:bg-white/5"
                                    >
                                        <TableCell className="font-bold">{pos?.symbol || 'Unknown'}</TableCell>
                                        <TableCell>
                                            <span className={cn(
                                                "px-2 py-1 rounded text-xs font-bold",
                                                pos?.side === 'LONG' ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                                            )}>
                                                {pos?.side || 'FLAT'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-right font-mono text-muted-foreground">${(pos?.entry_price || 0).toFixed(2)}</TableCell>
                                        <TableCell className="text-right font-mono">${(pos?.current_price || 0).toFixed(2)}</TableCell>
                                        <TableCell className="text-right font-mono">{pos?.quantity || 0}</TableCell>
                                        <TableCell className={cn("text-right font-bold font-mono", (pos?.pnl || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                                            {(pos?.pnl || 0) >= 0 ? '+' : ''}{(pos?.pnl || 0).toFixed(2)} ({(pos?.pnl_percent || 0).toFixed(2)}%)
                                        </TableCell>
                                    </motion.tr>
                                ))
                            )}
                        </AnimatePresence>
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
