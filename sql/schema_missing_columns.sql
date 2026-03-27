-- ============================================================
-- PMC ADMISSION SYSTEM — MISSING COLUMNS MIGRATION
-- Run these in your Supabase SQL editor (Tables > SQL Editor)
-- Each block is safe to re-run (uses IF NOT EXISTS / DO blocks)
-- ============================================================

-- ============================================================
-- TABLE: enquiry
-- Missing: notes, status (may already exist), source, subject,
--          preferred_course, student_name, whatsapp_number, email
-- ============================================================
ALTER TABLE enquiry
  ADD COLUMN IF NOT EXISTS status          TEXT DEFAULT 'open',
  ADD COLUMN IF NOT EXISTS notes           TEXT,
  ADD COLUMN IF NOT EXISTS source          TEXT,
  ADD COLUMN IF NOT EXISTS subject         TEXT,
  ADD COLUMN IF NOT EXISTS preferred_course TEXT,
  ADD COLUMN IF NOT EXISTS student_name    TEXT,
  ADD COLUMN IF NOT EXISTS whatsapp_number TEXT,
  ADD COLUMN IF NOT EXISTS email           TEXT;

-- ============================================================
-- TABLE: students
-- Missing: father_name, mother_name, gender, date_of_birth,
--          aadhar_number, emis_number, plus2_register_number,
--          plus2_school_name, plus2_marks, plus2_percentage,
--          plus2_year, board, group_studied, community,
--          religion, caste, general_quota, medium_of_study,
--          study_state, mother_tongue, category_7_5,
--          first_graduate, reference_details, unique_id
-- ============================================================
ALTER TABLE students
  ADD COLUMN IF NOT EXISTS unique_id           TEXT,
  ADD COLUMN IF NOT EXISTS father_name         TEXT,
  ADD COLUMN IF NOT EXISTS mother_name         TEXT,
  ADD COLUMN IF NOT EXISTS gender              TEXT,
  ADD COLUMN IF NOT EXISTS date_of_birth       DATE,
  ADD COLUMN IF NOT EXISTS aadhar_number       TEXT,
  ADD COLUMN IF NOT EXISTS emis_number         TEXT,
  ADD COLUMN IF NOT EXISTS plus2_register_number TEXT,
  ADD COLUMN IF NOT EXISTS plus2_school_name   TEXT,
  ADD COLUMN IF NOT EXISTS plus2_marks         NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS plus2_percentage    NUMERIC(5,2),
  ADD COLUMN IF NOT EXISTS plus2_year          INTEGER,
  ADD COLUMN IF NOT EXISTS board               TEXT,
  ADD COLUMN IF NOT EXISTS group_studied       TEXT,
  ADD COLUMN IF NOT EXISTS community           TEXT,
  ADD COLUMN IF NOT EXISTS religion            TEXT,
  ADD COLUMN IF NOT EXISTS caste               TEXT,
  ADD COLUMN IF NOT EXISTS general_quota       TEXT,
  ADD COLUMN IF NOT EXISTS medium_of_study     TEXT,
  ADD COLUMN IF NOT EXISTS study_state         TEXT,
  ADD COLUMN IF NOT EXISTS mother_tongue       TEXT,
  ADD COLUMN IF NOT EXISTS category_7_5        BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS first_graduate      BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS reference_details   TEXT;

-- ============================================================
-- TABLE: academics
-- Missing: practical1, practical2, theory, maths_voc,
--          cutoff, tnea_average, tnea_eligible,
--          language_subject_name, language_subject_marks,
--          maths_marks, physics_marks, chemistry_marks
-- ============================================================
ALTER TABLE academics
  ADD COLUMN IF NOT EXISTS maths_marks           NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS physics_marks         NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS chemistry_marks       NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS language_subject_name TEXT,
  ADD COLUMN IF NOT EXISTS language_subject_marks NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS practical1            NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS practical2            NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS theory                NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS maths_voc             NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS cutoff                NUMERIC(7,2),
  ADD COLUMN IF NOT EXISTS tnea_average          NUMERIC(6,2),
  ADD COLUMN IF NOT EXISTS tnea_eligible         TEXT;

-- ============================================================
-- TABLE: admissions (branch selection)
-- Missing: preferred_dept_id, optional_dept_ids,
--          allotted_dept_id, status, processed_at
-- ============================================================
ALTER TABLE admissions
  ADD COLUMN IF NOT EXISTS preferred_dept_id   INTEGER REFERENCES departments(id),
  ADD COLUMN IF NOT EXISTS optional_dept_ids   JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS allotted_dept_id    INTEGER REFERENCES departments(id),
  ADD COLUMN IF NOT EXISTS status              TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS processed_at        TIMESTAMPTZ;

-- ============================================================
-- TABLE: admission_applications
-- Status / tracking columns
-- ============================================================
ALTER TABLE admission_applications
  ADD COLUMN IF NOT EXISTS application_status  TEXT DEFAULT 'submitted',
  ADD COLUMN IF NOT EXISTS document_count      INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS notes               TEXT;

-- ============================================================
-- TABLE: counselling_records
-- Missing: allotment_order_number, consortium_number,
--          allotted_dept_id, quota_type, gq/mq fields
-- ============================================================
ALTER TABLE counselling_records
  ADD COLUMN IF NOT EXISTS allotment_order_number TEXT,
  ADD COLUMN IF NOT EXISTS consortium_number      TEXT,
  ADD COLUMN IF NOT EXISTS quota_type             TEXT,
  ADD COLUMN IF NOT EXISTS allotted_dept_id       INTEGER REFERENCES departments(id),
  ADD COLUMN IF NOT EXISTS allotted_department_name TEXT,
  ADD COLUMN IF NOT EXISTS gq_application_number  TEXT,
  ADD COLUMN IF NOT EXISTS gq_applied_at          TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS gq_round               TEXT,
  ADD COLUMN IF NOT EXISTS mq_consortium_number   TEXT,
  ADD COLUMN IF NOT EXISTS mq_applied_at          TIMESTAMPTZ;

-- ============================================================
-- TABLE: payments
-- Missing: bill_no, mode_of_payment, student_id, amount
-- ============================================================
ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS bill_no           TEXT,
  ADD COLUMN IF NOT EXISTS mode_of_payment   TEXT DEFAULT 'cash',
  ADD COLUMN IF NOT EXISTS amount            NUMERIC(12,2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS student_id        INTEGER REFERENCES students(id),
  ADD COLUMN IF NOT EXISTS payment_status    TEXT DEFAULT 'paid';

-- ============================================================
-- TABLE: documents
-- Ensure all core columns exist
-- ============================================================
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS document_type       TEXT,
  ADD COLUMN IF NOT EXISTS document_url        TEXT,
  ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS student_id          INTEGER REFERENCES students(id);

-- ============================================================
-- VERIFICATION: check columns were created successfully
-- ============================================================
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('enquiry','students','academics','admissions',
                     'admission_applications','counselling_records',
                     'payments','documents')
  AND table_schema = 'public'
ORDER BY table_name, ordinal_position;
