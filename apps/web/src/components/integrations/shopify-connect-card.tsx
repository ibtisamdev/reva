'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, Loader2, RefreshCw, Unplug } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  disconnectShopify,
  getShopifyInstallUrl,
  getShopifyStatus,
  shopifyKeys,
  triggerShopifySync,
} from '@/lib/api/shopify';
import { productKeys } from '@/lib/api/products';
import { useRequiredStoreId } from '@/lib/store-context';

export function ShopifyConnectCard() {
  const storeId = useRequiredStoreId();
  const queryClient = useQueryClient();
  const [shopDomain, setShopDomain] = useState('');

  const { data: connection, isLoading } = useQuery({
    queryKey: shopifyKeys.status(storeId),
    queryFn: () => getShopifyStatus(storeId),
  });

  const syncMutation = useMutation({
    mutationFn: () => triggerShopifySync(storeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shopifyKeys.status(storeId) });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: () => disconnectShopify(storeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shopifyKeys.status(storeId) });
      queryClient.invalidateQueries({ queryKey: productKeys.all });
    },
  });

  const isConnected = connection?.status === 'active';

  const handleConnect = async () => {
    const domain = shopDomain.includes('.myshopify.com')
      ? shopDomain
      : `${shopDomain}.myshopify.com`;
    const url = await getShopifyInstallUrl(storeId, domain);
    window.location.href = url;
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Shopify</CardTitle>
            <CardDescription>
              Connect your Shopify store to sync products and pages
            </CardDescription>
          </div>
          <Badge variant={isConnected ? 'default' : 'secondary'}>
            {isConnected ? 'Connected' : 'Not Connected'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {isConnected ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Store:</span>{' '}
                <span className="font-medium">{connection.platform_domain}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Products synced:</span>{' '}
                <span className="font-medium">{connection.product_count}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Last sync:</span>{' '}
                <span className="font-medium">
                  {connection.last_synced_at
                    ? new Date(connection.last_synced_at).toLocaleString()
                    : 'Never'}
                </span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Resync Products
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
              >
                <Unplug className="mr-2 h-4 w-4" />
                Disconnect
              </Button>
              <Button variant="outline" size="sm" asChild>
                <a
                  href={`https://${connection.platform_domain}/admin`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Shopify Admin
                </a>
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="shop-domain">Shop Domain</Label>
              <div className="flex gap-2">
                <Input
                  id="shop-domain"
                  placeholder="mystore"
                  value={shopDomain}
                  onChange={(e) => setShopDomain(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && shopDomain && handleConnect()}
                />
                <span className="flex items-center text-sm text-muted-foreground">
                  .myshopify.com
                </span>
              </div>
            </div>
            <Button onClick={handleConnect} disabled={!shopDomain}>
              Connect Shopify
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
