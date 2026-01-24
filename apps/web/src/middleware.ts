import { NextResponse, type NextRequest } from 'next/server';
import { getSessionCookie } from 'better-auth/cookies';

// Routes that require authentication
const protectedRoutes = ['/dashboard', '/settings'];

// Routes that should redirect to dashboard if authenticated
const authRoutes = ['/sign-in', '/sign-up'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for session cookie (optimistic check - actual validation happens in pages)
  const sessionCookie = getSessionCookie(request);
  const isAuthenticated = !!sessionCookie;

  // Redirect authenticated users away from auth pages
  if (isAuthenticated && authRoutes.some((route) => pathname.startsWith(route))) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Redirect unauthenticated users to sign in
  if (!isAuthenticated && protectedRoutes.some((route) => pathname.startsWith(route))) {
    const signInUrl = new URL('/sign-in', request.url);
    signInUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(signInUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes (except auth)
    '/(api(?!/auth))(.*)',
  ],
};
