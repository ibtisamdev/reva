'use client';

import { usePathname } from 'next/navigation';

import { UserMenu } from '@/components/auth/user-menu';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Overview',
  '/dashboard/conversations': 'Conversations',
  '/dashboard/knowledge': 'Knowledge Base',
  '/dashboard/settings/widget': 'Widget Settings',
};

export function DashboardHeader() {
  const pathname = usePathname();

  // Find the matching title (exact match or parent match for dynamic routes)
  const title =
    pageTitles[pathname] ||
    Object.entries(pageTitles).find(([path]) => pathname.startsWith(path))?.[1] ||
    'Dashboard';

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <h1 className="text-xl font-semibold text-foreground">{title}</h1>
      <UserMenu />
    </header>
  );
}
