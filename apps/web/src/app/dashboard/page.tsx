import { headers } from 'next/headers';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { auth } from '@/lib/auth';

export default async function DashboardPage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  const userName = session?.user?.name || 'User';

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Welcome back, {userName}!</CardTitle>
          <CardDescription>
            Your AI-powered customer support dashboard. Here&apos;s an overview of your store&apos;s
            support activity.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Conversations</CardDescription>
                <CardTitle className="text-3xl">0</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Knowledge Articles</CardDescription>
                <CardTitle className="text-3xl">0</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Active Sessions</CardDescription>
                <CardTitle className="text-3xl">0</CardTitle>
              </CardHeader>
            </Card>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Getting Started</CardTitle>
          <CardDescription>Complete these steps to set up your AI support agent.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                1
              </div>
              <div>
                <p className="font-medium">Add knowledge base content</p>
                <p className="text-sm text-muted-foreground">
                  Upload FAQs, policies, and product information.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-muted-foreground">
                2
              </div>
              <div>
                <p className="font-medium">Customize your widget</p>
                <p className="text-sm text-muted-foreground">
                  Set colors, welcome message, and position.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-muted-foreground">
                3
              </div>
              <div>
                <p className="font-medium">Install on your store</p>
                <p className="text-sm text-muted-foreground">
                  Copy the embed code to your Shopify theme.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
