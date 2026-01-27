'use client';

import { MessageSquare, Send, X } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { WidgetSettings } from '@/lib/api/types';

interface WidgetPreviewProps {
  settings: WidgetSettings;
}

export function WidgetPreview({ settings }: WidgetPreviewProps) {
  const isLeft = settings.position === 'bottom-left';

  return (
    <div className="relative h-[400px] rounded-lg border bg-gradient-to-b from-muted/50 to-muted overflow-hidden">
      {/* Simulated page content */}
      <div className="absolute inset-4 rounded-md border bg-background/80 p-4">
        <div className="h-4 w-3/4 rounded bg-muted" />
        <div className="mt-2 h-3 w-1/2 rounded bg-muted" />
        <div className="mt-4 space-y-2">
          <div className="h-3 w-full rounded bg-muted" />
          <div className="h-3 w-5/6 rounded bg-muted" />
          <div className="h-3 w-4/6 rounded bg-muted" />
        </div>
      </div>

      {/* Widget Chat Window */}
      <div
        className={cn(
          'absolute bottom-16 w-72 rounded-lg border bg-background shadow-lg',
          isLeft ? 'left-4' : 'right-4'
        )}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between rounded-t-lg px-4 py-3 text-white"
          style={{ backgroundColor: settings.primary_color }}
        >
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            <span className="font-medium">{settings.agent_name}</span>
          </div>
          <button className="rounded p-1 hover:bg-white/10">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Messages area */}
        <div className="h-40 p-3 space-y-2">
          {/* Welcome message */}
          <div className="flex gap-2">
            <div
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white text-xs"
              style={{ backgroundColor: settings.primary_color }}
            >
              R
            </div>
            <div className="rounded-lg bg-muted px-3 py-2 text-xs">
              {settings.welcome_message}
            </div>
          </div>
        </div>

        {/* Input area */}
        <div className="flex items-center gap-2 border-t px-3 py-2">
          <input
            type="text"
            placeholder="Type a message..."
            className="flex-1 text-xs bg-transparent outline-none"
            disabled
          />
          <button
            className="rounded p-1.5 text-white"
            style={{ backgroundColor: settings.primary_color }}
          >
            <Send className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Widget Button */}
      <div
        className={cn(
          'absolute bottom-4',
          isLeft ? 'left-4' : 'right-4'
        )}
      >
        <button
          className="flex h-12 w-12 items-center justify-center rounded-full text-white shadow-lg"
          style={{ backgroundColor: settings.primary_color }}
        >
          <MessageSquare className="h-6 w-6" />
        </button>
      </div>
    </div>
  );
}
