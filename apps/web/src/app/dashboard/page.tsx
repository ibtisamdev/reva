import { UserButton } from '@clerk/nextjs';

export default function DashboardPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <h1 className="text-xl font-bold">Reva Dashboard</h1>
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>
      <main className="container mx-auto p-8">
        <div className="rounded-lg border p-8 text-center">
          <h2 className="mb-4 text-2xl font-semibold">Welcome to Reva!</h2>
          <p className="text-muted-foreground">
            Your AI-powered customer support dashboard. Connect your Shopify store to get started.
          </p>
        </div>
      </main>
    </div>
  );
}
