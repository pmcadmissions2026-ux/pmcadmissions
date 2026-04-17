-- ============================================================
--  Basic Enquiry Table — PMC Admissions
--  Run this once in your Supabase SQL editor
-- ============================================================

-- 1. Create the basic_enquiry table for quick initial data capture
CREATE TABLE IF NOT EXISTS public.basic_enquiry (
  id                BIGSERIAL PRIMARY KEY,
  date              DATE NOT NULL DEFAULT CURRENT_DATE,
  full_name         TEXT NOT NULL,
  gender            TEXT,
  whatsapp_number   TEXT,
  date_of_birth     DATE,
  mother_tongue     TEXT,
  father_name       TEXT,
  father_phone      TEXT,
  mother_name       TEXT,
  mother_phone      TEXT,
  school_10_name    TEXT,
  school_10_place   TEXT,
  school_12_name    TEXT,
  school_12_place   TEXT,
  reference_type    TEXT,
  reference_name    TEXT,
  student_id        BIGINT REFERENCES public.students(id) ON DELETE CASCADE,
  added_to_enquiry  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Enable Row Level Security
ALTER TABLE public.basic_enquiry ENABLE ROW LEVEL SECURITY;

-- 3. Policy: allow full access for service_role (used by server.js)
DROP POLICY IF EXISTS "Service role full access" ON public.basic_enquiry;
CREATE POLICY "Service role full access" ON public.basic_enquiry
  FOR ALL
  USING (auth.role() = 'service_role');

-- 4. Helpful index for searching by name
CREATE INDEX IF NOT EXISTS basic_enquiry_full_name_idx
  ON public.basic_enquiry (lower(full_name));

-- ============================================================
--  Add reference_name column to enquiries table
--  (stores the referrer's name alongside the existing source/type)
-- ============================================================
ALTER TABLE public.enquiries
  ADD COLUMN IF NOT EXISTS reference_name TEXT;

-- If basic_enquiry table already exists, add student_id column
ALTER TABLE public.basic_enquiry
  ADD COLUMN IF NOT EXISTS student_id BIGINT REFERENCES public.students(id) ON DELETE CASCADE;
