'use client';

import { formatDistanceToNow } from 'date-fns';
import { FileText, MoreVertical, Pencil, Trash2 } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { KnowledgeArticle } from '@/lib/api/types';

interface KnowledgeCardProps {
  article: KnowledgeArticle;
  onDelete: () => void;
  isDeleting?: boolean;
}

const contentTypeLabels: Record<string, string> = {
  faq: 'FAQ',
  policy: 'Policy',
  guide: 'Guide',
  page: 'Page',
};

export function KnowledgeCard({ article, onDelete, isDeleting }: KnowledgeCardProps) {
  const timeAgo = formatDistanceToNow(new Date(article.created_at), { addSuffix: true });
  const isProcessing = article.chunks_count === 0;

  return (
    <Card className={isDeleting ? 'opacity-50' : undefined}>
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Link
                href={`/dashboard/knowledge/${article.id}`}
                className="font-medium hover:underline"
              >
                {article.title}
              </Link>
              <Badge variant="secondary" className="text-xs">
                {contentTypeLabels[article.content_type] || article.content_type}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Uploaded {timeAgo}
              {!isProcessing && ` • ${article.chunks_count} chunks`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isProcessing ? (
            <Badge variant="warning" className="animate-pulse">
              Processing...
            </Badge>
          ) : (
            <Badge variant="success">Ready</Badge>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" disabled={isDeleting}>
                <MoreVertical className="h-4 w-4" />
                <span className="sr-only">Actions</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/dashboard/knowledge/${article.id}`}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={onDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
}
