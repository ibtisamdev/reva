'use client';

import { format } from 'date-fns';
import { Calendar, Mail, MessageSquare, User } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ConversationDetail, ConversationStatus } from '@/lib/api/types';

interface CustomerSidebarProps {
  conversation: ConversationDetail;
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

export function CustomerSidebar({ conversation }: CustomerSidebarProps) {
  const status = statusConfig[conversation.status];
  const customerName = conversation.customer_name || 'Anonymous';
  const messageCount = conversation.messages.length;
  const createdDate = format(new Date(conversation.created_at), 'MMM d, yyyy');

  return (
    <div className="space-y-4">
      {/* Customer Info Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Customer Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{customerName}</span>
          </div>
          {conversation.customer_email && (
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm truncate">{conversation.customer_email}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">First seen: {createdDate}</span>
          </div>
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              {messageCount} message{messageCount !== 1 ? 's' : ''}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Conversation Details Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Conversation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge variant={status.variant}>{status.label}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Channel</span>
            <span className="text-sm">
              {channelLabels[conversation.channel] || conversation.channel}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-sm text-muted-foreground">Session ID</span>
            <code className="text-xs bg-muted px-2 py-1 rounded break-all">
              {conversation.session_id}
            </code>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
