'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Store as StoreIcon } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { createStore, storeKeys } from '@/lib/api/stores';
import { useStore } from '@/lib/store-context';

export function StoreSelector() {
  const { stores, selectedStore, isLoading, selectStore, refreshStores } = useStore();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newStoreName, setNewStoreName] = useState('');
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createStore,
    onSuccess: async (newStore) => {
      await queryClient.invalidateQueries({ queryKey: storeKeys.list() });
      await refreshStores();
      selectStore(newStore.id);
      setIsCreateOpen(false);
      setNewStoreName('');
      toast.success('Store created successfully');
    },
    onError: (error) => {
      toast.error('Failed to create store', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    },
  });

  const handleCreateStore = () => {
    if (newStoreName.trim()) {
      createMutation.mutate({ name: newStoreName.trim() });
    }
  };

  if (isLoading) {
    return (
      <div className="border-b p-3">
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  // Don't render if no stores - pages will show NoStoreState component instead
  if (stores.length === 0) {
    return null;
  }

  return (
    <>
      <div className="border-b p-3">
        <Select
          value={selectedStore?.id ?? ''}
          onValueChange={(value) => {
            if (value === '__create__') {
              setIsCreateOpen(true);
            } else {
              selectStore(value);
            }
          }}
        >
          <SelectTrigger className="w-full">
            <div className="flex items-center gap-2">
              <StoreIcon className="h-4 w-4 shrink-0" />
              <SelectValue placeholder="Select a store">
                <span className="truncate">{selectedStore?.name ?? 'Select a store'}</span>
              </SelectValue>
            </div>
          </SelectTrigger>
          <SelectContent>
            {stores.map((store) => (
              <SelectItem key={store.id} value={store.id}>
                <div className="flex items-center gap-2">
                  <StoreIcon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{store.name}</span>
                </div>
              </SelectItem>
            ))}
            <SelectSeparator />
            <SelectItem value="__create__" className="text-primary">
              <div className="flex items-center gap-2">
                <Plus className="h-4 w-4 shrink-0" />
                <span>Create new store</span>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Store</DialogTitle>
            <DialogDescription>
              Add a new store to your organization. Each store has its own knowledge base and
              conversations.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="store-name">Store Name</Label>
              <Input
                id="store-name"
                placeholder="My Online Store"
                value={newStoreName}
                onChange={(e) => setNewStoreName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !createMutation.isPending) {
                    handleCreateStore();
                  }
                }}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateStore}
              disabled={!newStoreName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Store'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
