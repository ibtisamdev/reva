'use client';

import { useCallback, useState } from 'react';

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
import type { ContentType } from '@/lib/api/types';

interface PdfUploadFormProps {
  onSubmit: (formData: FormData) => void;
  isLoading?: boolean;
}

export function PdfUploadForm({ onSubmit, isLoading }: PdfUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [contentType, setContentType] = useState<ContentType>('guide');
  const [dragActive, setDragActive] = useState(false);

  const handleFile = (f: File | null) => {
    if (f && f.type === 'application/pdf') {
      setFile(f);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFile(droppedFile || null);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    if (title.trim()) formData.append('title', title.trim());
    formData.append('content_type', contentType);

    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        {file ? (
          <div className="text-center">
            <p className="font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024).toFixed(0)} KB
            </p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => setFile(null)}
              disabled={isLoading}
            >
              Remove
            </Button>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Drag and drop a PDF here, or
            </p>
            <label htmlFor="pdf-file" className="cursor-pointer">
              <span className="text-sm font-medium text-primary underline">
                browse files
              </span>
              <input
                id="pdf-file"
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0] || null)}
                disabled={isLoading}
              />
            </label>
            <p className="mt-1 text-xs text-muted-foreground">PDF up to 10 MB</p>
          </div>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="pdf-title">Title (optional)</Label>
          <Input
            id="pdf-title"
            placeholder="Uses filename if empty"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="pdf-content-type">Content Type</Label>
          <Select
            value={contentType}
            onValueChange={(value) => setContentType(value as ContentType)}
            disabled={isLoading}
          >
            <SelectTrigger id="pdf-content-type">
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
        <Button type="submit" disabled={!file || isLoading}>
          {isLoading ? 'Uploading...' : 'Upload PDF'}
        </Button>
      </div>
    </form>
  );
}
