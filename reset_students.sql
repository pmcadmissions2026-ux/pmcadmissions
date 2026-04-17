-- ╔═══════════════════════════════════════════════════════════════════════╗
-- ║  reset_students.sql                                                    ║
-- ║  WARNING: Permanently deletes ALL student and admission data.          ║
-- ║  Only run this when you want a completely fresh start.                 ║
-- ║  Run in Supabase → SQL Editor.                                         ║
-- ╚═══════════════════════════════════════════════════════════════════════╝

-- Step 1: Remove all dependent data first (order matters for FK constraints)
TRUNCATE TABLE
  public.documents,
  public.payments,
  public.counselling_records,
  public.admission_applications,
  public.admissions,
  public.academics,
  public.enquiries,
  public.students
RESTART IDENTITY CASCADE;

-- Step 2: Reset the unique_id sequence if a dedicated sequence exists
-- (The server uses generateUniqueStudentId() which scans existing IDs,
--  so after TRUNCATE the next auto-generated ID will restart from PMC{YY}001{YY}.)
ALTER SEQUENCE IF EXISTS public.students_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.academics_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.enquiries_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.admissions_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.admission_applications_app_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.counselling_records_counselling_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.documents_doc_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS public.payments_payment_id_seq RESTART WITH 1;

-- Step 3: Verify all tables are empty  
SELECT 'students'              AS tbl, COUNT(*) AS rows FROM public.students
UNION ALL
SELECT 'academics',             COUNT(*) FROM public.academics
UNION ALL
SELECT 'enquiries',             COUNT(*) FROM public.enquiries
UNION ALL
SELECT 'admissions',            COUNT(*) FROM public.admissions
UNION ALL
SELECT 'admission_applications',COUNT(*) FROM public.admission_applications
UNION ALL
SELECT 'counselling_records',   COUNT(*) FROM public.counselling_records
UNION ALL
SELECT 'documents',             COUNT(*) FROM public.documents
UNION ALL
SELECT 'payments',              COUNT(*) FROM public.payments;
