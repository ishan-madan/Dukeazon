#!/bin/bash

set -euo pipefail

mypath=$(realpath "$0")
mybase=$(dirname "$mypath")
cd "$mybase"

datadir="${1:-data/}"
if [ ! -d "$datadir" ] ; then
    echo "$datadir does not exist under $mybase" >&2
    exit 1
fi

set -a
source ../.flaskenv
set +a

createdb --version >/dev/null 2>&1 || { echo "PostgreSQL client utilities not found" >&2; exit 1; }
pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" >/dev/null 2>&1 || { echo "PostgreSQL server not reachable at $DB_HOST:${DB_PORT:-5432}" >&2; exit 1; }

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\"" >/dev/null
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\"" >/dev/null

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -f create.sql >/dev/null
cd "$datadir"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -f "$mybase/load.sql" >/dev/null

echo "Database $DB_NAME has been recreated and seeded."
