'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { createKnowledgeArticle, knowledgeKeys } from '@/lib/api/knowledge';
import type { CreateKnowledgeRequest } from '@/lib/api/types';

import { TextUploadForm } from './text-upload-form';

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  storeId: string;
}

export function UploadDialog({ open, onOpenChange, storeId }: UploadDialogProps) {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: CreateKnowledgeRequest) => createKnowledgeArticle(storeId, data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      onOpenChange(false);

      if (response.status === 'processing') {
        toast.info('Document queued for processing', {
          description: 'Large documents are processed in the background.',
        });
      } else {
        toast.success('Article created successfully');
      }
    },
    onError: (error) => {
      toast.error('Failed to create article', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Knowledge Content</DialogTitle>
          <DialogDescription>
            Add content to your knowledge base to help your AI agent answer questions.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="text" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="text">Text</TabsTrigger>
            <TabsTrigger value="pdf" disabled>
              PDF (coming soon)
            </TabsTrigger>
            <TabsTrigger value="url" disabled>
              URL (coming soon)
            </TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="mt-4">
            <TextUploadForm
              onSubmit={(data) => createMutation.mutate(data)}
              isLoading={createMutation.isPending}
            />
          </TabsContent>

          <TabsContent value="pdf" className="mt-4">
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
              <p className="text-muted-foreground">PDF upload coming soon</p>
            </div>
          </TabsContent>

          <TabsContent value="url" className="mt-4">
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
              <p className="text-muted-foreground">URL import coming soon</p>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
