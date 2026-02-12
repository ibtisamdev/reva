'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  analyticsKeys,
  getWismoInquiries,
  getWismoSummary,
  getWismoTrend,
} from '@/lib/api/analytics';
import { useRequiredStoreId } from '@/lib/store-context';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export default function OrderInquiriesPage() {
  const storeId = useRequiredStoreId();
  const [page, setPage] = useState(1);

  const {
    data: summary,
    isLoading: summaryLoading,
  } = useQuery({
    queryKey: analyticsKeys.wismoSummary(storeId),
    queryFn: () => getWismoSummary(storeId),
  });

  const { data: trend } = useQuery({
    queryKey: analyticsKeys.wismoTrend(storeId),
    queryFn: () => getWismoTrend(storeId),
  });

  const {
    data: inquiriesData,
    isLoading: inquiriesLoading,
  } = useQuery({
    queryKey: analyticsKeys.wismoInquiries(storeId, page),
    queryFn: () => getWismoInquiries(storeId, { page, pageSize: 20 }),
  });

  const maxTrendCount = trend ? Math.max(...trend.map((d) => d.count), 1) : 1;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Order Inquiries</h1>
        <p className="text-muted-foreground">
          WISMO analytics and order status inquiry tracking
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Inquiries
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary?.total_inquiries ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Resolution Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary ? `${Math.round(summary.resolution_rate * 100)}%` : '0%'}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Per Day
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary?.avg_per_day ?? 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {summary?.period_days ?? 30} days
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trend Display */}
      {trend && trend.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Daily Trend (Last 30 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-32 items-end gap-1">
              {trend.map((day) => (
                <div
                  key={day.date}
                  className="flex flex-1 flex-col items-center gap-1"
                >
                  <div
                    className="w-full rounded-t bg-primary transition-all"
                    style={{
                      height: `${(day.count / maxTrendCount) * 100}%`,
                      minHeight: day.count > 0 ? '4px' : '0px',
                    }}
                    title={`${day.date}: ${day.count} inquiries`}
                  />
                </div>
              ))}
            </div>
            <div className="mt-2 flex justify-between text-xs text-muted-foreground">
              <span>{trend[0]?.date}</span>
              <span>{trend[trend.length - 1]?.date}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inquiries Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Recent Inquiries
          </CardTitle>
        </CardHeader>
        <CardContent>
          {inquiriesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !inquiriesData?.items.length ? (
            <p className="py-8 text-center text-muted-foreground">
              No order inquiries yet. They will appear here when customers ask
              about their orders.
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-3 pr-4 font-medium">Date</th>
                      <th className="pb-3 pr-4 font-medium">Order #</th>
                      <th className="pb-3 pr-4 font-medium">Email</th>
                      <th className="pb-3 pr-4 font-medium">Type</th>
                      <th className="pb-3 pr-4 font-medium">Status</th>
                      <th className="pb-3 font-medium">Resolution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inquiriesData.items.map((inq) => (
                      <tr key={inq.id} className="border-b last:border-0">
                        <td className="py-3 pr-4">
                          {new Date(inq.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs">
                          {inq.order_number ?? '-'}
                        </td>
                        <td className="py-3 pr-4 max-w-[200px] truncate">
                          {inq.customer_email ?? '-'}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant="outline">
                            {inq.inquiry_type.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4">
                          {inq.fulfillment_status ? (
                            <Badge variant="secondary">
                              {inq.fulfillment_status}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="py-3">
                          {inq.resolution ? (
                            <Badge
                              variant={
                                inq.resolution === 'answered' ||
                                inq.resolution === 'tracking_provided'
                                  ? 'default'
                                  : inq.resolution === 'verification_failed'
                                    ? 'destructive'
                                    : 'secondary'
                              }
                            >
                              {inq.resolution.replace('_', ' ')}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {inquiriesData.pages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Page {inquiriesData.page} of {inquiriesData.pages} ({inquiriesData.total} total)
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
                        setPage((p) => Math.min(inquiriesData.pages, p + 1))
                      }
                      disabled={page >= inquiriesData.pages}
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
