'use client';

import { format } from 'date-fns';
import { Bot, User, ExternalLink } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { Message, SourceReference } from '@/lib/api/types';

interface MessageBubbleProps {
  message: Message;
}

function SourceCitation({ source }: { source: SourceReference }) {
  return (
    <div className="mt-2 rounded-md border bg-muted/50 p-2 text-xs">
      <div className="flex items-center gap-1 font-medium">
        <span className="truncate">{source.title}</span>
        {source.url && (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 text-primary hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
      {source.snippet && (
        <p className="mt-1 text-muted-foreground line-clamp-2">{source.snippet}</p>
      )}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const timestamp = format(new Date(message.created_at), 'h:mm a');

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <span className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Message content */}
      <div
        className={cn(
          'flex max-w-[75%] flex-col',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        <div
          className={cn(
            'rounded-lg px-4 py-2',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground'
          )}
        >
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        </div>

        {/* Sources (for assistant messages) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1 w-full space-y-1">
            {message.sources.map((source, index) => (
              <SourceCitation key={source.chunk_id || `source-${index}`} source={source} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="mt-1 text-xs text-muted-foreground">{timestamp}</span>
      </div>
    </div>
  );
}
