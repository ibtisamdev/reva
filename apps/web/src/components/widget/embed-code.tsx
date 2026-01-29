'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

interface EmbedCodeProps {
  storeId: string;
}

export function EmbedCode({ storeId }: EmbedCodeProps) {
  const [copied, setCopied] = useState(false);

  // Generate the embed code
  const embedCode = `<!-- Reva Support Widget -->
<script>
  window.RevaConfig = {
    storeId: '${storeId}'
  };
</script>
<script
  src="${process.env.NEXT_PUBLIC_WIDGET_URL || 'https://widget.getreva.ai'}/widget.js"
  async
></script>`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(embedCode);
      setCopied(true);
      toast.success('Embed code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy embed code');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Embed Code</CardTitle>
        <CardDescription>
          Add this code to your Shopify theme, just before the closing{' '}
          <code className="text-xs bg-muted px-1 py-0.5 rounded">&lt;/body&gt;</code> tag.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs font-mono">
            <code>{embedCode}</code>
          </pre>
          <Button
            variant="secondary"
            size="sm"
            className="absolute right-2 top-2"
            onClick={handleCopy}
          >
            {copied ? (
              <>
                <Check className="mr-1.5 h-3.5 w-3.5" />
                Copied
              </>
            ) : (
              <>
                <Copy className="mr-1.5 h-3.5 w-3.5" />
                Copy
              </>
            )}
          </Button>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          For Shopify: Go to Online Store &rarr; Themes &rarr; Edit code &rarr;
          theme.liquid
        </p>
      </CardContent>
    </Card>
  );
}
