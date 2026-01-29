'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  deleteKnowledgeArticle,
  getKnowledgeArticles,
  knowledgeKeys,
} from '@/lib/api/knowledge';
import type { KnowledgeArticle } from '@/lib/api/types';

import { EmptyState } from './empty-state';
import { KnowledgeCard } from './knowledge-card';
import { UploadDialog } from './upload-dialog';

interface KnowledgeListProps {
  storeId: string;
}

export function KnowledgeList({ storeId }: KnowledgeListProps) {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [deleteArticle, setDeleteArticle] = useState<KnowledgeArticle | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: knowledgeKeys.list(storeId),
    queryFn: () => getKnowledgeArticles(storeId),
    // Auto-poll while any article is processing
    refetchInterval: (query) => {
      const hasProcessing = query.state.data?.items.some((a) => a.chunks_count === 0);
      return hasProcessing ? 2000 : false;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (articleId: string) => deleteKnowledgeArticle(articleId, storeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      toast.success('Article deleted');
      setDeleteArticle(null);
    },
    onError: (error) => {
      toast.error('Failed to delete article', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  const handleDeleteClick = (article: KnowledgeArticle) => {
    setDeleteArticle(article);
  };

  const handleDeleteConfirm = () => {
    if (deleteArticle) {
      deleteMutation.mutate(deleteArticle.id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const articles = data?.items || [];
  const hasProcessing = articles.some((a) => a.chunks_count === 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Knowledge Base</h2>
          <p className="text-muted-foreground">
            Manage your store&apos;s knowledge articles for AI responses.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasProcessing && (
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isRefetching}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          )}
          <Button onClick={() => setIsUploadOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Content
          </Button>
        </div>
      </div>

      {articles.length === 0 ? (
        <EmptyState onAddClick={() => setIsUploadOpen(true)} />
      ) : (
        <div className="space-y-3">
          {articles.map((article) => (
            <KnowledgeCard
              key={article.id}
              article={article}
              onDelete={() => handleDeleteClick(article)}
              isDeleting={deleteMutation.isPending && deleteMutation.variables === article.id}
            />
          ))}
        </div>
      )}

      <UploadDialog open={isUploadOpen} onOpenChange={setIsUploadOpen} storeId={storeId} />

      <Dialog open={!!deleteArticle} onOpenChange={(open) => !open && setDeleteArticle(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Article</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{deleteArticle?.title}&quot;? This action cannot
              be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteArticle(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
