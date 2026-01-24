import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="mb-4 text-4xl font-bold">Reva</h1>
        <p className="mb-8 text-lg text-muted-foreground">
          AI-powered customer support for your Shopify store
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/sign-in"
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="inline-flex h-10 items-center justify-center rounded-md border border-input bg-background px-8 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            Sign Up
          </Link>
        </div>
      </div>
    </main>
  );
}
