# Complete Admission Portal Requirements & Implementation Guide

## Overview
Three-step admission process with comprehensive data collection at each stage.

---

## STEP 1: ENQUIRY (Student Registration)

### Fields to be Collected:

**Personal Information**
1. Full Name *
2. Unique ID (e.g., 26000127) *
3. Student WhatsApp Number *
4. Father Name + Father Contact Number
5. Mother Name + Mother Contact Number
6. Student Email *
7. Date of Birth
8. Gender
9. Permanent Address
10. City, State, Pincode

**Educational Background**
1. 10th School Name
2. 10th Marks Secured
3. 10th Percentage
4. 10th Year (Passing Year)
5. +2 School Name
6. +2 Marks Secured
7. +2 Percentage
8. +2 Year (Passing Year)
9. Board (CBSE/State Board)
10. Study State
11. Group Studied (MPCB/MPCC/Vocational)

**Social & Reservations**
1. Religion
2. Community/Caste
3. Mother Tongue
4. 7.5 Category (Yes/No)
5. First Graduate Status (Yes/No)
6. General/Merit/Quota (GQ/MQ)
7. Reference Details

**Additional Information**
1. Aadhar Number
2. Medium of Study

### Calculated Fields:
- **Cutoff Score** = Maths Marks + ((Physics + Chemistry) / 2)

### Database: `students` table
All above fields stored with prefix adjustments (e.g., tenth_*, plus2_*)

---

## STEP 2: BRANCH SELECTION

### Fields Required:
1. Student Name (from Step 1)
2. Unique ID (from Step 1)
3. **Preferred Department (Mandatory)** - Primary choice
4. **Optional Department** - Secondary choice if primary full
5. Community (display from Step 1)
6. Category (7.5/General - from Step 1)
7. School Name (from Step 1)
8. Cutoff Score (calculated from Step 1)
9. Status: `branch_selection_pending` → `branch_allotted`

### Database: `admissions` table
- Links students to departments
- Tracks preferred vs final allotted department
- Status tracking through workflow

### Department Information Display:
Available seats by quota:
- General Seats
- Reserved Seats
- Management Seats
- Total Available Seats

---

## STEP 3: APPLICATION FILING (Final Review)

### Fields to Display:
1. Student Name (from Step 1)
2. Application Number (auto-generated)
3. Unique ID (from Step 1)
4. Selected Department (from Step 2)
5. Completion Status
6. Final Submission Button
7. PDF Download Option

### Actions:
- Review all entered data
- Download Application Summary as PDF
- Save as Draft OR Submit Final
- Locked after submission (review period notification)

### Database: `admission_applications` table
- Final application record
- Status: `completed`
- Timestamp of submission

---

## DATABASE SCHEMA

### SQL Instructions to Execute in Supabase:

```sql
-- Step 1: Add missing fields to students table
ALTER TABLE public.students 
ADD COLUMN IF NOT EXISTS father_phone text,
ADD COLUMN IF NOT EXISTS mother_phone text,
ADD COLUMN IF NOT EXISTS mother_tongue text,
ADD COLUMN IF NOT EXISTS caste text,
ADD COLUMN IF NOT EXISTS tenth_school_name text,
ADD COLUMN IF NOT EXISTS tenth_marks numeric,
ADD COLUMN IF NOT EXISTS tenth_percentage numeric,
ADD COLUMN IF NOT EXISTS tenth_year integer,
ADD COLUMN IF NOT EXISTS plus2_school_name text,
ADD COLUMN IF NOT EXISTS plus2_marks numeric,
ADD COLUMN IF NOT EXISTS plus2_percentage numeric,
ADD COLUMN IF NOT EXISTS plus2_year integer,
ADD COLUMN IF NOT EXISTS board text,
ADD COLUMN IF NOT EXISTS study_state text,
ADD COLUMN IF NOT EXISTS group_studied text,
ADD COLUMN IF NOT EXISTS medium_of_study text,
ADD COLUMN IF NOT EXISTS category_7_5 boolean default false,
ADD COLUMN IF NOT EXISTS first_graduate boolean default false,
ADD COLUMN IF NOT EXISTS general_quota text,
ADD COLUMN IF NOT EXISTS reference_details text,
ADD COLUMN IF NOT EXISTS aadhar_number text,
ADD COLUMN IF NOT EXISTS status text default 'pending';

-- Step 2: Create departments table
CREATE TABLE IF NOT EXISTS public.departments (
  id bigserial primary key,
  dept_code text unique not null,
  dept_name text not null,
  short_name text,
  description text,
  is_active boolean default true,
  created_at timestamp with time zone default now()
) TABLESPACE pg_default;

-- Step 3: Create seats table for department quotas
CREATE TABLE IF NOT EXISTS public.seats (
  id bigserial primary key,
  department_id bigint not null references public.departments(id),
  quota_type text not null, -- 'general', 'reserved', 'management', 'nri'
  total_seats integer not null,
  available_seats integer not null,
  filled_seats integer default 0,
  academic_year text,
  created_at timestamp with time zone default now(),
  constraint seats_unique_dept_quota unique(department_id, quota_type)
) TABLESPACE pg_default;

-- Step 4: Create admissions table for branch selection
CREATE TABLE IF NOT EXISTS public.admissions (
  id bigserial primary key,
  student_id bigint not null references public.students(id),
  preferred_dept_id bigint not null references public.departments(id),
  optional_dept_id bigint references public.departments(id),
  selected_dept_id bigint references public.departments(id),
  status text default 'branch_selection_pending',
  allotment_date timestamp with time zone,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
) TABLESPACE pg_default;

-- Step 5: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_admissions_student_id ON public.admissions(student_id);
CREATE INDEX IF NOT EXISTS idx_admissions_status ON public.admissions(status);
CREATE INDEX IF NOT EXISTS idx_seats_department_id ON public.seats(department_id);
CREATE INDEX IF NOT EXISTS idx_departments_active ON public.departments(is_active);
```

---

## WORKFLOW FLOW

```
LOGIN (Admission Coordinator)
    ↓
DASHBOARD (/admin/admission-controller)
    ↓
NEW ENQUIRY (/admin/enquiries/new)
    ↓
STEP 1: Complete enquiry form
    ↓ [Submit]
STEP 2: Branch Selection (/admin/enquiry_step2/<id>)
    ↓ [Select Preferred & Optional Departments]
STEP 3: Application Filing (/admin/enquiry_step3/<id>)
    ↓ [Review & Submit]
COMPLETION
    ↓
Back to Dashboard showing all applications
```

---

## CURRENT STATUS

### ✅ COMPLETED:
- Step 1 form template (new_enquiry.html) with all 20+ fields
- Step 2 form template (enquiry_step2.html) with department selection
- Database schema ALTER TABLE statements provided
- Student info display with cutoff calculation
- Department seats display table
- Material Symbols icons & Lexend font styling

### ⏳ TODO - NEXT STEPS:

1. **Execute SQL Schema** (Supabase Dashboard → SQL Editor)
   - Run all ALTER TABLE and CREATE TABLE statements
   - Populate departments table with your college departments
   - Create seats records for each department per quota

2. **Test End-to-End Workflow**
   - Create new enquiry → Fill Step 1 → Submit
   - Verify Step 2 loads with departments
   - Submit department selection
   - Verify Step 3 displays correctly

3. **Add Sample Data**
   - 5-10 departments
   - Seat counts per department (general, reserved, management)

4. **Fine-tuning**
   - Adjust cutoff calculation if needed
   - Customize reservation categories
   - Add validation rules

---

## KEY DATABASE RELATIONSHIPS

```
students (1) ──→ (many) admissions
  ↓
  Step 1 data

admissions (many) ──→ (1) departments
  ↓
  Preferred & Optional links

departments (1) ──→ (many) seats
  ↓
  Quota breakdown
```

---

## FILE STRUCTURE

```
templates/admin/
├── new_enquiry.html        [Step 1 - Enquiry Form]
├── enquiry_step2.html      [Step 2 - Branch Selection]
├── enquiry_step3.html      [Step 3 - Application Filing]
└── admission_controller_dashboard.html

admin/routes.py
├── new_enquiry()           [POST handler for Step 1]
├── enquiry_step2()         [GET/POST for Step 2]
└── enquiry_step3()         [GET/POST for Step 3]
```

---

## NEXT REQUIREMENTS

Please provide:
1. Your college's department names & codes
2. Number of seats per department per quota
3. Any additional fields needed in Step 1 or 2
4. Specific validation rules for each field
5. Step 3 requirements (print format, document requirements, etc.)

---

