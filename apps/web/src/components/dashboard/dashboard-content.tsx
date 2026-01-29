'use client';

import { Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';

import { NoStoreState } from '@/components/dashboard/no-store-state';
import { useStore } from '@/lib/store-context';

export function DashboardContent({ children }: { children: ReactNode }) {
  const { isLoading, hasStores, selectedStoreId } = useStore();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!hasStores || !selectedStoreId) {
    return <NoStoreState />;
  }

  return <>{children}</>;
}
