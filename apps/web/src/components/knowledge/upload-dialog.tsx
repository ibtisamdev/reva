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
import {
  createKnowledgeArticle,
  createKnowledgeFromPdf,
  createKnowledgeFromUrl,
  knowledgeKeys,
} from '@/lib/api/knowledge';
import type { CreateKnowledgeFromUrlRequest, CreateKnowledgeRequest } from '@/lib/api/types';

import { PdfUploadForm } from './pdf-upload-form';
import { TextUploadForm } from './text-upload-form';
import { UrlUploadForm } from './url-upload-form';

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  storeId: string;
}

export function UploadDialog({ open, onOpenChange, storeId }: UploadDialogProps) {
  const queryClient = useQueryClient();

  const onIngestionSuccess = (status: string) => {
    queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
    onOpenChange(false);

    if (status === 'processing') {
      toast.info('Document queued for processing', {
        description: 'Large documents are processed in the background.',
      });
    } else {
      toast.success('Article created successfully');
    }
  };

  const onIngestionError = (error: unknown) => {
    toast.error('Failed to create article', {
      description: error instanceof Error ? error.message : 'Unknown error',
    });
  };

  const textMutation = useMutation({
    mutationFn: (data: CreateKnowledgeRequest) => createKnowledgeArticle(storeId, data),
    onSuccess: (response) => onIngestionSuccess(response.status),
    onError: onIngestionError,
  });

  const urlMutation = useMutation({
    mutationFn: (data: CreateKnowledgeFromUrlRequest) => createKnowledgeFromUrl(storeId, data),
    onSuccess: (response) => onIngestionSuccess(response.status),
    onError: onIngestionError,
  });

  const pdfMutation = useMutation({
    mutationFn: (formData: FormData) => createKnowledgeFromPdf(storeId, formData),
    onSuccess: (response) => onIngestionSuccess(response.status),
    onError: onIngestionError,
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
            <TabsTrigger value="pdf">PDF</TabsTrigger>
            <TabsTrigger value="url">URL</TabsTrigger>
          </TabsList>

          <TabsContent value="text" className="mt-4">
            <TextUploadForm
              onSubmit={(data) => textMutation.mutate(data)}
              isLoading={textMutation.isPending}
            />
          </TabsContent>

          <TabsContent value="pdf" className="mt-4">
            <PdfUploadForm
              onSubmit={(formData) => pdfMutation.mutate(formData)}
              isLoading={pdfMutation.isPending}
            />
          </TabsContent>

          <TabsContent value="url" className="mt-4">
            <UrlUploadForm
              onSubmit={(data) => urlMutation.mutate(data)}
              isLoading={urlMutation.isPending}
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
