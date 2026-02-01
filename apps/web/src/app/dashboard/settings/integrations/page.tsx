'use client';

import { ShopifyConnectCard } from '@/components/integrations/shopify-connect-card';

export default function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your e-commerce platform to sync products and content
        </p>
      </div>
      <ShopifyConnectCard />
    </div>
  );
}
