import { headers } from 'next/headers';
import { redirect } from 'next/navigation';

import { Providers } from '@/app/providers';
import { DashboardHeader } from '@/components/dashboard/header';
import { Sidebar } from '@/components/dashboard/sidebar';
import { Toaster } from '@/components/ui/sonner';
import { auth } from '@/lib/auth';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect('/sign-in');
  }

  return (
    <Providers>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col">
          <DashboardHeader />
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
      <Toaster />
    </Providers>
  );
}
