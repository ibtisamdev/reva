'use client';

import { ConversationList } from '@/components/conversations/conversation-list';
import { useRequiredStoreId } from '@/lib/store-context';

export default function ConversationsPage() {
  const storeId = useRequiredStoreId();

  return <ConversationList storeId={storeId} />;
}
