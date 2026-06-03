-- Creates a NON-superuser, NON-BYPASSRLS application role.
--
-- This is security-critical: Postgres RLS is ignored by superusers and by roles
-- with BYPASSRLS. The default POSTGRES_USER (sfqa) is a superuser used ONLY for
-- migrations. The application connects as sfqa_app, which is subject to RLS.
--
-- Runs automatically on first container start (docker-entrypoint-initdb.d).

CREATE ROLE sfqa_app WITH LOGIN PASSWORD 'sfqa_app_dev_only' NOSUPERUSER NOBYPASSRLS;

GRANT CONNECT ON DATABASE sfqa TO sfqa_app;
GRANT USAGE ON SCHEMA public TO sfqa_app;

-- Privileges on current and future tables/sequences created by the migration
-- role (sfqa). Migrations run as sfqa; the app uses only DML as sfqa_app.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sfqa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sfqa_app;

ALTER DEFAULT PRIVILEGES FOR ROLE sfqa IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sfqa_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sfqa IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO sfqa_app;
