-- ============================================================
--  PMC ADMISSION — Row Level Security (RLS) Policies
--  Run this in Supabase SQL Editor (Dashboard > SQL Editor)
--  Your Node.js backend uses the service_role key which
--  BYPASSES RLS automatically. These policies only affect
--  direct anon-key requests (e.g. from the browser).
-- ============================================================

-- ─────────────────────────────────────────────
-- 1. ENABLE RLS ON ALL TABLES
-- ─────────────────────────────────────────────
ALTER TABLE public.academics              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admission_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admissions             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.counselling_records    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.departments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seats                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.session_log            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.students               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users                  ENABLE ROW LEVEL SECURITY;


-- ─────────────────────────────────────────────
-- 2. DROP EXISTING POLICIES (clean slate)
-- ─────────────────────────────────────────────
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT policyname, tablename
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN (
        'academics','admission_applications','admissions',
        'counselling_records','departments','documents',
        'payments','roles','seats','session_log','students','users'
      )
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', r.policyname, r.tablename);
  END LOOP;
END $$;


-- ─────────────────────────────────────────────
-- 3. academics
--    Backend: full via service_role (bypasses RLS)
--    Frontend (anon): read-only
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_academics"
  ON public.academics FOR SELECT
  TO anon
  USING (true);

-- Block anon writes
CREATE POLICY "deny_anon_insert_academics"
  ON public.academics FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_academics"
  ON public.academics FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_academics"
  ON public.academics FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 4. admission_applications
--    Frontend: read-only (admin dashboard uses anon key)
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_admission_applications"
  ON public.admission_applications FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_admission_applications"
  ON public.admission_applications FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_admission_applications"
  ON public.admission_applications FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_admission_applications"
  ON public.admission_applications FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 5. admissions
--    Frontend: read-only
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_admissions"
  ON public.admissions FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_admissions"
  ON public.admissions FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_admissions"
  ON public.admissions FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_admissions"
  ON public.admissions FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 6. counselling_records
--    Frontend: read-only
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_counselling_records"
  ON public.counselling_records FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_counselling_records"
  ON public.counselling_records FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_counselling_records"
  ON public.counselling_records FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_counselling_records"
  ON public.counselling_records FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 7. departments
--    Public reference data — anon can read freely
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_departments"
  ON public.departments FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_departments"
  ON public.departments FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_departments"
  ON public.departments FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_departments"
  ON public.departments FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 8. documents
--    SENSITIVE — anon cannot read or write.
--    All access goes through Node.js backend (service_role).
-- ─────────────────────────────────────────────
CREATE POLICY "deny_anon_select_documents"
  ON public.documents FOR SELECT
  TO anon
  USING (false);

CREATE POLICY "deny_anon_insert_documents"
  ON public.documents FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_documents"
  ON public.documents FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_documents"
  ON public.documents FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 9. payments
--    SENSITIVE — anon cannot read or write.
--    All access goes through Node.js backend (service_role).
-- ─────────────────────────────────────────────
CREATE POLICY "deny_anon_select_payments"
  ON public.payments FOR SELECT
  TO anon
  USING (false);

CREATE POLICY "deny_anon_insert_payments"
  ON public.payments FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_payments"
  ON public.payments FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_payments"
  ON public.payments FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 10. roles
--     Public reference data — anon can read
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_roles"
  ON public.roles FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_roles"
  ON public.roles FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_roles"
  ON public.roles FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_roles"
  ON public.roles FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 11. seats
--     Public reference data — anon can read (seat availability)
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_seats"
  ON public.seats FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_seats"
  ON public.seats FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_seats"
  ON public.seats FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_seats"
  ON public.seats FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 12. session_log
--     SENSITIVE — anon has NO access whatsoever.
-- ─────────────────────────────────────────────
CREATE POLICY "deny_anon_select_session_log"
  ON public.session_log FOR SELECT
  TO anon
  USING (false);

CREATE POLICY "deny_anon_insert_session_log"
  ON public.session_log FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_session_log"
  ON public.session_log FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_session_log"
  ON public.session_log FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 13. students
--     Frontend: read-only (admin dashboard).
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_students"
  ON public.students FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_students"
  ON public.students FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_students"
  ON public.students FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_students"
  ON public.students FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- 14. users
--     Frontend reads this directly (admin loads own profile with anon key).
--     Read-only. Writes go through backend only.
-- ─────────────────────────────────────────────
CREATE POLICY "anon_select_users"
  ON public.users FOR SELECT
  TO anon
  USING (true);

CREATE POLICY "deny_anon_insert_users"
  ON public.users FOR INSERT
  TO anon
  WITH CHECK (false);

CREATE POLICY "deny_anon_update_users"
  ON public.users FOR UPDATE
  TO anon
  USING (false);

CREATE POLICY "deny_anon_delete_users"
  ON public.users FOR DELETE
  TO anon
  USING (false);


-- ─────────────────────────────────────────────
-- SUMMARY
-- ─────────────────────────────────────────────
-- anon SELECT  ✅ : academics, admission_applications, admissions,
--                   counselling_records, departments, roles, seats,
--                   students, users
-- anon SELECT  ❌ : documents, payments, session_log  (sensitive)
-- anon WRITE   ❌ : ALL tables  (must go through Node.js backend)
-- service_role    : BYPASSES RLS — full access to all tables
-- ─────────────────────────────────────────────
