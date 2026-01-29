'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { ArrowLeft, Loader2, Save, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { NoStoreState } from '@/components/dashboard/no-store-state';
import {
  deleteKnowledgeArticle,
  getKnowledgeArticle,
  knowledgeKeys,
  updateKnowledgeArticle,
} from '@/lib/api/knowledge';
import type { ContentType, UpdateKnowledgeRequest } from '@/lib/api/types';
import { useRequiredStoreId } from '@/lib/store-context';

export default function KnowledgeEditPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const articleId = params.id as string;
  const storeId = useRequiredStoreId();

  const [title, setTitle] = useState('');
  const [contentType, setContentType] = useState<ContentType>('faq');
  const [sourceUrl, setSourceUrl] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data: article, isLoading } = useQuery({
    queryKey: knowledgeKeys.detail(storeId ?? '', articleId),
    queryFn: () => getKnowledgeArticle(articleId, storeId!),
    enabled: !!storeId,
  });

  // Populate form when article loads
  useEffect(() => {
    if (article) {
      setTitle(article.title);
      setContentType(article.content_type);
      setSourceUrl(article.source_url || '');
    }
  }, [article]);

  const updateMutation = useMutation({
    mutationFn: (data: UpdateKnowledgeRequest) =>
      updateKnowledgeArticle(articleId, storeId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.all });
      toast.success('Article updated');
    },
    onError: (error) => {
      toast.error('Failed to update article', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteKnowledgeArticle(articleId, storeId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      toast.success('Article deleted');
      router.push('/dashboard/knowledge');
    },
    onError: (error) => {
      toast.error('Failed to delete article', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  // Show onboarding when no store is selected
  if (!storeId) {
    return <NoStoreState />;
  }

  const handleSave = () => {
    const data: UpdateKnowledgeRequest = {};
    if (title !== article?.title) data.title = title;
    if (contentType !== article?.content_type) data.content_type = contentType;
    if (sourceUrl !== (article?.source_url || '')) data.source_url = sourceUrl || undefined;

    if (Object.keys(data).length > 0) {
      updateMutation.mutate(data);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate();
    setShowDeleteDialog(false);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!article) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">Article not found</p>
        <Button asChild variant="outline">
          <Link href="/dashboard/knowledge">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Knowledge Base
          </Link>
        </Button>
      </div>
    );
  }

  const timeAgo = formatDistanceToNow(new Date(article.created_at), { addSuffix: true });
  const isProcessing = article.chunks_count === 0;
  const hasChanges =
    title !== article.title ||
    contentType !== article.content_type ||
    sourceUrl !== (article.source_url || '');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button asChild variant="ghost" size="icon">
            <Link href="/dashboard/knowledge">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h2 className="text-2xl font-bold">Edit Article</h2>
            <p className="text-sm text-muted-foreground">Created {timeAgo}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isProcessing ? (
            <Badge variant="warning" className="animate-pulse">
              Processing...
            </Badge>
          ) : (
            <Badge variant="success">Ready • {article.chunks_count} chunks</Badge>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Article Details</CardTitle>
              <CardDescription>
                Update the article metadata. Content changes require re-uploading.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={updateMutation.isPending}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="content-type">Content Type</Label>
                  <Select
                    value={contentType}
                    onValueChange={(value) => setContentType(value as ContentType)}
                    disabled={updateMutation.isPending}
                  >
                    <SelectTrigger id="content-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="faq">FAQ</SelectItem>
                      <SelectItem value="policy">Policy</SelectItem>
                      <SelectItem value="guide">Guide</SelectItem>
                      <SelectItem value="page">Page</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="source-url">Source URL</Label>
                  <Input
                    id="source-url"
                    type="url"
                    placeholder="https://..."
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    disabled={updateMutation.isPending}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Content Preview</Label>
                <Textarea
                  value={article.content}
                  readOnly
                  rows={10}
                  className="bg-muted font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Content cannot be edited. To update content, delete this article and create a new
                  one.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                className="w-full"
                onClick={handleSave}
                disabled={!hasChanges || updateMutation.isPending}
              >
                {updateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Save Changes
              </Button>
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Article
              </Button>
            </CardContent>
          </Card>

          {article.chunks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Chunks</CardTitle>
                <CardDescription>
                  Content is split into chunks for better retrieval.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {article.chunks.slice(0, 5).map((chunk) => (
                    <div
                      key={chunk.id}
                      className="rounded-md bg-muted p-2 text-xs text-muted-foreground"
                    >
                      <span className="font-medium">Chunk {chunk.chunk_index + 1}:</span>{' '}
                      {chunk.content.slice(0, 100)}...
                    </div>
                  ))}
                  {article.chunks.length > 5 && (
                    <p className="text-xs text-muted-foreground">
                      + {article.chunks.length - 5} more chunks
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Article</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{article.title}&quot;? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
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
