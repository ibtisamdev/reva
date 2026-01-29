'use client';

import { KnowledgeList } from '@/components/knowledge/knowledge-list';
import { useRequiredStoreId } from '@/lib/store-context';

export default function KnowledgePage() {
  const storeId = useRequiredStoreId();

  return <KnowledgeList storeId={storeId} />;
}
