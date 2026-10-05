#!/usr/bin/env bash
# Apply the schema to Neon. init.sql is idempotent, so this is safe to run on every deploy.
# Uses the DIRECT (non-pooled) URL because DDL should not go through the connection pooler.
set -euo pipefail
: "${AML_POSTGRES_MIGRATE_URL:?export AML_POSTGRES_MIGRATE_URL (direct Neon connection string)}"
psql "$AML_POSTGRES_MIGRATE_URL" -v ON_ERROR_STOP=1 -q -f infra/postgres/init.sql
echo "schema applied"
