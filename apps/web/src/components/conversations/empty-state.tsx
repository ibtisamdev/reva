import { MessageSquare } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';

interface EmptyStateProps {
  hasFilters?: boolean;
}

export function ConversationsEmptyState({ hasFilters = false }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-16">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <MessageSquare className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-lg font-semibold">
          {hasFilters ? 'No conversations found' : 'No conversations yet'}
        </h3>
        <p className="mt-2 max-w-sm text-center text-sm text-muted-foreground">
          {hasFilters
            ? 'Try adjusting your search or filters to find what you\'re looking for.'
            : 'Conversations will appear here once customers start chatting with your support widget.'}
        </p>
      </CardContent>
    </Card>
  );
}
