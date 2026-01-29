#!/bin/bash
set -e

if [ -z "$CONDUCTOR_ROOT_PATH" ]; then
  echo "Error: CONDUCTOR_ROOT_PATH is not set" >&2
  exit 1
fi

ENV_STORE="$CONDUCTOR_ROOT_PATH/.conductor-env"

# First-time setup: create env store and seed from .env.example
if [ ! -d "$ENV_STORE" ]; then
  echo "First-time setup: creating env files from .env.example templates..."
  mkdir -p "$ENV_STORE/apps/api" "$ENV_STORE/apps/web"
  trap 'rm -rf "$ENV_STORE"; echo "Setup failed, cleaned up partial env store." >&2' ERR
  cp .env.example "$ENV_STORE/.env"
  cp apps/api/.env.example "$ENV_STORE/apps/api/.env"
  cp apps/web/.env.example "$ENV_STORE/apps/web/.env"
  trap - ERR
  echo "⚠ Please edit the .env files in $ENV_STORE with your actual values."
fi

# Symlink env files into workspace
ln -sf "$ENV_STORE/.env" .env
ln -sf "$ENV_STORE/apps/api/.env" apps/api/.env
ln -sf "$ENV_STORE/apps/web/.env" apps/web/.env

echo "✓ .env files linked from $ENV_STORE"
