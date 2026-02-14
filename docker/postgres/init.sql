-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create separate database for Better Auth
CREATE DATABASE reva_auth;

-- Connect to reva_auth and add extensions
\c reva_auth
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create separate database for tests
CREATE DATABASE reva_test;
\c reva_test
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
