-- Database initialization script for AI获客
-- Executed on first PostgreSQL container start

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Seed: Default copywriting templates for new users (stored in app, this is DB init only)
-- The actual tables are created by SQLAlchemy on first run.
-- This file ensures the database and extensions are ready.

-- Placeholder for future migrations via Alembic
SELECT 'AI获客 database initialized successfully' AS status;
