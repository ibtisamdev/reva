'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Store as StoreIcon } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { organization, useSession } from '@/lib/auth-client';
import { createStore, storeKeys } from '@/lib/api/stores';
import { useStore } from '@/lib/store-context';

export function NoStoreState() {
  const [storeName, setStoreName] = useState('');
  const { selectStore, refreshStores } = useStore();
  const queryClient = useQueryClient();
  const { data: session } = useSession();

  const createMutation = useMutation({
    mutationFn: async (name: string) => {
      // Check if user has an active organization, create one if not
      const activeOrg = await organization.getFullOrganization();

      if (!activeOrg.data) {
        // No active organization - create one
        const userName = session?.user?.name || 'User';
        const orgName = `${userName}'s Organization`;
        const orgResult = await organization.create({
          name: orgName,
          slug: orgName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''),
        });

        if (orgResult.error) {
          throw new Error('Failed to create organization: ' + orgResult.error.message);
        }

        if (orgResult.data) {
          // Set the new organization as active
          await organization.setActive({ organizationId: orgResult.data.id });
        }
      }

      // Now create the store
      return createStore({ name });
    },
    onSuccess: async (newStore) => {
      await queryClient.invalidateQueries({ queryKey: storeKeys.list() });
      await refreshStores();
      selectStore(newStore.id);
      toast.success('Store created! Welcome to Reva.');
    },
    onError: (error) => {
      toast.error('Failed to create store', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (storeName.trim()) {
      createMutation.mutate(storeName.trim());
    }
  };

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary">
            <StoreIcon className="h-6 w-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">Welcome to Reva!</CardTitle>
          <CardDescription>
            Let&apos;s get started by creating your first store. Each store represents a brand or
            website you want to add AI support to.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="store-name">Store Name</Label>
              <Input
                id="store-name"
                placeholder="e.g., My Shopify Store"
                value={storeName}
                onChange={(e) => setStoreName(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                This is how you&apos;ll identify this store in your dashboard.
              </p>
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={!storeName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Store'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
