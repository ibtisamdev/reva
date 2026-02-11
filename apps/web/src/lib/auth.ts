import { betterAuth } from 'better-auth';
import { getMigrations } from 'better-auth/db';
import { nextCookies } from 'better-auth/next-js';
import { jwt, organization } from 'better-auth/plugins';
import { Pool } from 'pg';

const authConfig = {
  database: new Pool({
    connectionString: process.env.AUTH_DATABASE_URL,
  }),

  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Set to true in production
  },

  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID || '',
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
    },
  },

  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session every 24 hours
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 minutes
    },
  },

  user: {
    additionalFields: {
      role: {
        type: 'string',
        required: false,
        defaultValue: 'member',
        input: false, // Don't allow setting via signup
      },
    },
  },

  plugins: [
    organization({
      allowUserToCreateOrganization: true,
      organizationCreation: {
        disabled: false,
      },
    }),
    jwt({
      jwks: {
        keyPairConfig: {
          alg: 'RS256',
        },
      },
      jwt: {
        definePayload: ({ user, session }) => ({
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          activeOrganizationId: session.activeOrganizationId,
        }),
      },
    }),
    nextCookies(), // Must be last
  ],

  trustedOrigins: [
    'http://localhost:3000',
    'http://localhost:8000',
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.NEXT_PUBLIC_API_URL,
  ].filter((origin): origin is string => Boolean(origin)),
} satisfies Parameters<typeof betterAuth>[0];

// Run migrations on startup (idempotent — only applies pending migrations)
getMigrations(authConfig)
  .then(({ runMigrations }) => runMigrations())
  .catch((err) => {
    console.error('[auth] Failed to run migrations:', err);
  });

export const auth = betterAuth(authConfig);

export type Session = typeof auth.$Infer.Session;
export type User = typeof auth.$Infer.Session.user;
