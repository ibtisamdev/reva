'use client';

import { Loader2 } from 'lucide-react';

import { ConversationList } from '@/components/conversations/conversation-list';
import { NoStoreState } from '@/components/dashboard/no-store-state';
import { useStore } from '@/lib/store-context';

export default function ConversationsPage() {
  const { selectedStoreId, isLoading, hasStores } = useStore();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!hasStores) {
    return <NoStoreState />;
  }

  if (!selectedStoreId) {
    return null;
  }

  return <ConversationList storeId={selectedStoreId} />;
}
