import React from 'react';
import { cn } from '@/lib/utils';
import { Activity } from 'lucide-react';

export function Header({ status = 'online' }: { status?: 'online' | 'offline' | 'connecting' }) {
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
                {/* Status indicator */}
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
