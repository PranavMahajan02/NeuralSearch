#!/bin/sh
# Runs once, when the Postgres volume is first initialised (as the bootstrap
# superuser POSTGRES_USER). Creates the application role WITHOUT superuser,
# createdb or createrole rights, gives it its own database, and installs the
# extensions the migrations need (pgcrypto, pg_trgm) so the app role never needs
# elevated privileges. The superuser password is only used here and for backups.
set -eu

: "${APP_DB_USER:?APP_DB_USER is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"
: "${APP_DB_NAME:?APP_DB_NAME is required}"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" --dbname postgres \
     -v app_user="$APP_DB_USER" -v app_password="$APP_DB_PASSWORD" -v app_db="$APP_DB_NAME" <<'SQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE DATABASE :"app_db" OWNER :"app_user";
REVOKE ALL ON DATABASE :"app_db" FROM PUBLIC;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB_NAME" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL

echo "cogniseek: created role and database (non-superuser) with pgcrypto and pg_trgm"
