'use client';

import { use } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { MessageThread } from '@/components/conversations/message-thread';
import { CustomerSidebar } from '@/components/conversations/customer-sidebar';
import {
  getConversation,
  updateConversationStatus,
  conversationKeys,
} from '@/lib/api/conversations';
import { useRequiredStoreId } from '@/lib/store-context';

interface ConversationDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function ConversationDetailPage({
  params,
}: ConversationDetailPageProps) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const storeId = useRequiredStoreId();

  const { data: conversation, isLoading } = useQuery({
    queryKey: conversationKeys.detail(storeId, id),
    queryFn: () => getConversation(id, storeId),
    // Poll for active conversations to get new messages
    refetchInterval: (query) => {
      if (query.state.data?.status === 'active') {
        return 3000;
      }
      return false;
    },
  });

  const resolveStatusMutation = useMutation({
    mutationFn: () => updateConversationStatus(id, storeId, 'resolved'),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: conversationKeys.detail(storeId, id),
      });
      queryClient.invalidateQueries({
        queryKey: conversationKeys.lists(),
      });
      toast.success('Conversation marked as resolved');
    },
    onError: () => {
      toast.error('Failed to update conversation status');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <Skeleton className="h-[600px]" />
          <div className="space-y-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </div>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <h2 className="text-lg font-semibold">Conversation not found</h2>
        <p className="mt-2 text-muted-foreground">
          This conversation may have been deleted or doesn&apos;t exist.
        </p>
        <Button asChild className="mt-4">
          <Link href="/dashboard/conversations">Back to Conversations</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/conversations">
              <ArrowLeft className="h-5 w-5" />
              <span className="sr-only">Back to conversations</span>
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-semibold">
              {conversation.customer_name || conversation.customer_email || 'Anonymous'}
            </h1>
            {conversation.customer_email && conversation.customer_name && (
              <p className="text-sm text-muted-foreground">
                {conversation.customer_email}
              </p>
            )}
          </div>
        </div>
        {conversation.status !== 'resolved' && (
          <Button
            onClick={() => resolveStatusMutation.mutate()}
            disabled={resolveStatusMutation.isPending}
          >
            {resolveStatusMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle className="mr-2 h-4 w-4" />
            )}
            Mark Resolved
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        {/* Message Thread */}
        <Card className="flex h-[600px] flex-col overflow-hidden">
          <MessageThread messages={conversation.messages} />
        </Card>

        {/* Sidebar */}
        <CustomerSidebar conversation={conversation} />
      </div>
    </div>
  );
}
