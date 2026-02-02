'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { SearchInput } from '@/components/common/search-input';
import { Pagination } from '@/components/common/pagination';
import { ConversationCard } from './conversation-card';
import { ConversationsEmptyState } from './empty-state';
import { getConversations, conversationKeys } from '@/lib/api/conversations';
import type { ConversationStatus } from '@/lib/api/types';

interface ConversationListProps {
  storeId: string;
}

export function ConversationList({ storeId }: ConversationListProps) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<ConversationStatus | 'all'>('all');
  const [page, setPage] = useState(1);

  const filters = {
    status: status === 'all' ? undefined : status,
    search: search || undefined,
  };

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: [...conversationKeys.list(storeId, filters), page],
    queryFn: () =>
      getConversations(storeId, {
        status: filters.status,
        search: filters.search,
        page,
        pageSize: 20,
      }),
    // Poll for active conversations
    refetchInterval: (query) => {
      const hasActive = query.state.data?.items.some((c) => c.status === 'active');
      return hasActive ? 5000 : false;
    },
  });

  const handleStatusChange = (value: string) => {
    setStatus(value as ConversationStatus | 'all');
    setPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const hasFilters = search !== '' || status !== 'all';

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <SearchInput
          value={search}
          onChange={handleSearchChange}
          placeholder="Search by customer name or email..."
          className="w-full sm:w-64"
        />
        <div className="flex items-center gap-2">
          <Select value={status} onValueChange={handleStatusChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="escalated">Escalated</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            {isRefetching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="sr-only">Refresh</span>
          </Button>
        </div>
      </div>

      {/* List */}
      {data?.items.length === 0 ? (
        <ConversationsEmptyState hasFilters={hasFilters} />
      ) : (
        <>
          <div className="space-y-3">
            {data?.items.map((conversation) => (
              <ConversationCard key={conversation.id} conversation={conversation} />
            ))}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <Pagination
              currentPage={page}
              totalPages={data.pages}
              onPageChange={setPage}
            />
          )}

          {/* Summary */}
          {data && (
            <p className="text-center text-sm text-muted-foreground">
              Showing {data.items.length} of {data.total} conversation
              {data.total !== 1 ? 's' : ''}
            </p>
          )}
        </>
      )}
    </div>
  );
}
