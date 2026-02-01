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
import type { ContentType, CreateKnowledgeFromUrlRequest } from '@/lib/api/types';

interface UrlUploadFormProps {
  onSubmit: (data: CreateKnowledgeFromUrlRequest) => void;
  isLoading?: boolean;
}

export function UrlUploadForm({ onSubmit, isLoading }: UrlUploadFormProps) {
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [contentType, setContentType] = useState<ContentType>('page');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      url: url.trim(),
      title: title.trim() || undefined,
      content_type: contentType,
    });
  };

  const isValid = url.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="url">URL</Label>
        <Input
          id="url"
          type="url"
          placeholder="https://example.com/page"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading}
          required
        />
        <p className="text-xs text-muted-foreground">
          The page content will be fetched and converted to text automatically.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="url-title">Title (optional)</Label>
          <Input
            id="url-title"
            placeholder="Auto-detected from page"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="url-content-type">Content Type</Label>
          <Select
            value={contentType}
            onValueChange={(value) => setContentType(value as ContentType)}
            disabled={isLoading}
          >
            <SelectTrigger id="url-content-type">
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
      </div>

      <div className="flex justify-end pt-4">
        <Button type="submit" disabled={!isValid || isLoading}>
          {isLoading ? 'Importing...' : 'Import URL'}
        </Button>
      </div>
    </form>
  );
}
