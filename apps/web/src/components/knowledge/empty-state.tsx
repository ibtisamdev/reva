import { BookOpen } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  onAddClick: () => void;
}

export function EmptyState({ onAddClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
        <BookOpen className="h-6 w-6 text-primary" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">No knowledge articles yet</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Add FAQs, policies, and product information to help your AI agent answer customer
        questions accurately.
      </p>
      <Button onClick={onAddClick} className="mt-6">
        Add your first article
      </Button>
    </div>
  );
}
