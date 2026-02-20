'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getRecoverySequences,
  getRecoverySummary,
  getRecoverySettings,
  recoveryKeys,
  stopRecoverySequence,
  updateRecoverySettings,
} from '@/lib/api/recovery';
import type { RecoverySettings } from '@/lib/api/recovery';
import { useRequiredStoreId } from '@/lib/store-context';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function RecoveryPage() {
  const storeId = useRequiredStoreId();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: recoveryKeys.summary(storeId),
    queryFn: () => getRecoverySummary(storeId),
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: recoveryKeys.settings(storeId),
    queryFn: () => getRecoverySettings(storeId),
  });

  const { data: sequencesData, isLoading: sequencesLoading } = useQuery({
    queryKey: recoveryKeys.sequences(storeId, page),
    queryFn: () => getRecoverySequences(storeId, { page, pageSize: 20 }),
  });

  const toggleMutation = useMutation({
    mutationFn: (enabled: boolean) => {
      const updated: RecoverySettings = {
        ...(settings || {
          enabled: false,
          min_cart_value: 0,
          abandonment_threshold_minutes: 60,
          sequence_timing_minutes: [120, 1440, 2880, 4320],
          discount_enabled: false,
          discount_percent: 10,
          max_emails_per_day: 50,
          exclude_email_patterns: [],
        }),
        enabled,
      };
      return updateRecoverySettings(storeId, updated);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: recoveryKeys.settings(storeId) });
    },
  });

  const stopMutation = useMutation({
    mutationFn: (sequenceId: string) =>
      stopRecoverySequence(storeId, sequenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: recoveryKeys.sequences(storeId, page),
      });
      queryClient.invalidateQueries({ queryKey: recoveryKeys.summary(storeId) });
    },
  });

  const statusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'default';
      case 'completed':
        return 'secondary';
      case 'stopped':
        return 'destructive';
      default:
        return 'outline' as const;
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Cart Recovery</h1>
          <p className="text-muted-foreground">
            Recover abandoned checkouts with automated email sequences
          </p>
        </div>
        <div className="flex items-center gap-3">
          {settingsLoading ? (
            <Skeleton className="h-9 w-24" />
          ) : (
            <Button
              variant={settings?.enabled ? 'default' : 'outline'}
              onClick={() => toggleMutation.mutate(!settings?.enabled)}
              disabled={toggleMutation.isPending}
            >
              {settings?.enabled ? 'Enabled' : 'Disabled'}
            </Button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Recovery Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary
                  ? `${Math.round(summary.recovery_rate * 100)}%`
                  : '0%'}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Sequences
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary?.active_sequences ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Recovered Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                ${summary?.recovered_revenue?.toFixed(2) ?? '0.00'}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Emails Sent
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary?.emails_sent ?? 0}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sequences Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Recovery Sequences
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sequencesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !sequencesData?.items.length ? (
            <p className="py-8 text-center text-muted-foreground">
              No recovery sequences yet. They will appear here when abandoned
              checkouts are detected.
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-3 pr-4 font-medium">Email</th>
                      <th className="pb-3 pr-4 font-medium">Type</th>
                      <th className="pb-3 pr-4 font-medium">Step</th>
                      <th className="pb-3 pr-4 font-medium">Status</th>
                      <th className="pb-3 pr-4 font-medium">Started</th>
                      <th className="pb-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sequencesData.items.map((seq) => (
                      <tr key={seq.id} className="border-b last:border-0">
                        <td className="py-3 pr-4 max-w-[200px] truncate">
                          {seq.customer_email}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant="outline">
                            {seq.sequence_type.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs">
                          {seq.current_step_index} /{' '}
                          {seq.total_steps}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant={statusColor(seq.status)}>
                            {seq.status}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4">
                          {new Date(seq.started_at).toLocaleDateString()}
                        </td>
                        <td className="py-3">
                          {seq.status === 'active' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => stopMutation.mutate(seq.id)}
                              disabled={stopMutation.isPending}
                            >
                              Stop
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {sequencesData.pages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {sequencesData.page} of {sequencesData.pages} (
                    {sequencesData.total} total)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setPage((p) =>
                          Math.min(sequencesData.pages, p + 1)
                        )
                      }
                      disabled={page >= sequencesData.pages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
