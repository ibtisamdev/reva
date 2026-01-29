'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
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
import type { ContentType, CreateKnowledgeRequest } from '@/lib/api/types';

interface TextUploadFormProps {
  onSubmit: (data: CreateKnowledgeRequest) => void;
  isLoading?: boolean;
}

export function TextUploadForm({ onSubmit, isLoading }: TextUploadFormProps) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [contentType, setContentType] = useState<ContentType>('faq');
  const [sourceUrl, setSourceUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      title: title.trim(),
      content: content.trim(),
      content_type: contentType,
      source_url: sourceUrl.trim() || undefined,
    });
  };

  const isValid = title.trim().length > 0 && content.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          placeholder="e.g., Shipping Policy"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">Content</Label>
        <Textarea
          id="content"
          placeholder="Paste your content here..."
          rows={8}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={isLoading}
        />
        <p className="text-xs text-muted-foreground">
          {content.length.toLocaleString()} characters
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="content-type">Content Type</Label>
          <Select
            value={contentType}
            onValueChange={(value) => setContentType(value as ContentType)}
            disabled={isLoading}
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
          <Label htmlFor="source-url">Source URL (optional)</Label>
          <Input
            id="source-url"
            type="url"
            placeholder="https://..."
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <Button type="submit" disabled={!isValid || isLoading}>
          {isLoading ? 'Uploading...' : 'Upload'}
        </Button>
      </div>
    </form>
  );
}
