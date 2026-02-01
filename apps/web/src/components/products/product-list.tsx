'use client';

import Image from 'next/image';
import { ExternalLink, Package } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { Product } from '@/lib/api/types';

interface ProductListProps {
  products: Product[];
  shopDomain?: string;
}

export function ProductList({ products, shopDomain }: ProductListProps) {
  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="text-lg font-medium">No products synced</h3>
        <p className="text-sm text-muted-foreground">
          Connect your Shopify store to sync products
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {products.map((product) => {
        const firstImage = product.images?.[0];
        const firstVariant = product.variants?.[0];
        const price = firstVariant?.price;

        return (
          <Card key={product.id} className="overflow-hidden">
            <div className="relative aspect-square bg-muted">
              {firstImage ? (
                <Image
                  src={firstImage.src}
                  alt={firstImage.alt || product.title}
                  fill
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <Package className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium leading-tight line-clamp-2">
                  {product.title}
                </h3>
                {price && (
                  <span className="shrink-0 font-semibold">${price}</span>
                )}
              </div>
              <div className="mt-2 flex items-center gap-2">
                {product.vendor && (
                  <span className="text-xs text-muted-foreground">
                    {product.vendor}
                  </span>
                )}
                <Badge variant="secondary" className="text-xs">
                  {product.status}
                </Badge>
              </div>
              {shopDomain && (
                <a
                  href={`https://${shopDomain}/admin/products/${product.platform_product_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <ExternalLink className="h-3 w-3" />
                  Edit in Shopify
                </a>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
