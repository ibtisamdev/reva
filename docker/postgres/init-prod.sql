-- Production database initialization
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Auth database
CREATE DATABASE reva_auth;
\c reva_auth
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- GlitchTip database
\c reva
CREATE DATABASE glitchtip;
