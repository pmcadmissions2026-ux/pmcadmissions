-- Add vocational/practical fields to academics and a cutoff column to admissions
-- Run these in Supabase SQL editor or psql against your database.

BEGIN;

-- Add practical and theory marks to academics (if academics table stores per-student academic marks)
ALTER TABLE IF EXISTS academics
  ADD COLUMN IF NOT EXISTS practical1 numeric,
  ADD COLUMN IF NOT EXISTS practical2 numeric,
  ADD COLUMN IF NOT EXISTS theory numeric;

-- If you store a persisted cutoff on admissions, add a numeric cutoff column
ALTER TABLE IF EXISTS admissions
  ADD COLUMN IF NOT EXISTS cutoff numeric;

COMMIT;

-- Optional: set a default value (e.g., 0) if desired:
-- ALTER TABLE admissions ALTER COLUMN cutoff SET DEFAULT 0;

-- Note: adjust table names/schema if necessary for your DB.
