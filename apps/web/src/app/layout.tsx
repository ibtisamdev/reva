import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';

import '@/app/globals.css';

export const metadata: Metadata = {
  title: 'Reva - E-commerce AI Support',
  description: 'AI-powered customer support for your Shopify store',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="min-h-screen antialiased">{children}</body>
      </html>
    </ClerkProvider>
  );
}
