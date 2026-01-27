'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, User } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Conversation, ConversationStatus } from '@/lib/api/types';

interface ConversationCardProps {
  conversation: Conversation;
}

const statusConfig: Record<
  ConversationStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  active: { label: 'Active', variant: 'default' },
  resolved: { label: 'Resolved', variant: 'secondary' },
  escalated: { label: 'Escalated', variant: 'destructive' },
};

const channelLabels: Record<string, string> = {
  widget: 'Widget',
  email: 'Email',
  whatsapp: 'WhatsApp',
  sms: 'SMS',
};

export function ConversationCard({ conversation }: ConversationCardProps) {
  const status = statusConfig[conversation.status];
  const customerDisplay =
    conversation.customer_name || conversation.customer_email || 'Anonymous';
  const timeAgo = formatDistanceToNow(new Date(conversation.updated_at), {
    addSuffix: true,
  });

  return (
    <Link href={`/dashboard/conversations/${conversation.id}`}>
      <Card className="transition-colors hover:bg-muted/50">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                <User className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium truncate">{customerDisplay}</h3>
                  <Badge variant={status.variant} className="shrink-0">
                    {status.label}
                  </Badge>
                </div>
                {conversation.customer_email &&
                  conversation.customer_name && (
                    <p className="text-sm text-muted-foreground truncate">
                      {conversation.customer_email}
                    </p>
                  )}
                <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <MessageSquare className="h-3.5 w-3.5" />
                    {channelLabels[conversation.channel] || conversation.channel}
                  </span>
                  <span>Session: {conversation.session_id.slice(0, 8)}...</span>
                </div>
              </div>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-sm text-muted-foreground">{timeAgo}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
