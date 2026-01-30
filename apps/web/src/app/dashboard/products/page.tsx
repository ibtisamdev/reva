'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ProductList } from '@/components/products/product-list';
import { getProducts, productKeys } from '@/lib/api/products';
import { getShopifyStatus, shopifyKeys } from '@/lib/api/shopify';
import { useRequiredStoreId } from '@/lib/store-context';

export default function ProductsPage() {
  const storeId = useRequiredStoreId();
  const [page, setPage] = useState(1);

  const { data: connection } = useQuery({
    queryKey: shopifyKeys.status(storeId),
    queryFn: () => getShopifyStatus(storeId),
  });

  const { data, isLoading } = useQuery({
    queryKey: productKeys.list(storeId, page),
    queryFn: () => getProducts(storeId, { page }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Products</h1>
        <p className="text-muted-foreground">
          Products synced from your connected store
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <ProductList
            products={data?.items ?? []}
            shopDomain={connection?.platform_domain}
          />

          {data && data.pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
