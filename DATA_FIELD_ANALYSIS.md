# Student Profile Data Analysis - N/A Fields Diagnosis

## Problem Summary
Student profile PMC25000126 (SANJAYA KUMAY K) is showing N/A for many fields. This analysis identifies which database tables contain data and which fields are missing.

---

## Current Data Structure in Route

The `student_profiles()` route fetches data from these tables:
1. ✅ **students** - Personal information
2. ✅ **academics** - Academic details (HSC school, marks, percentage)
3. ✅ **enquiries** - Enquiry records
4. ✅ **admissions** - Department selection records
5. ✅ **admission_applications** - Application records
6. ✅ **documents** - Document tracking
7. ✅ **counselling_records** - Counselling records
8. ✅ **payments** - Payment records

---

## Field-by-Field Analysis

### Showing N/A Values for PMC25000126:

| Column | Template Field | Database Table | Expected Field | Status |
|--------|---|---|---|---|
| **DOB** | dob | students | date_of_birth | ❌ **MISSING** - Table has `date_of_birth` but field may be NULL |
| **HSC School** | hsc_school_name | academics | hsc_school_name | ⚠️ **NULL** - Field exists but no data entered |
| **HSC %** | hsc_percentage | academics | hsc_percentage | ⚠️ **NULL** - Field exists but no data entered |
| **Cutoff** | cutoff | academics | cutoff | ⚠️ **NULL** - Field exists but no data entered |
| **TNEA Eligible** | tnea_eligible | academics | tnea_eligible | ❌ **MISSING** - Field doesn't exist in academics table |
| **TNEA Avg** | tnea_average | academics | tnea_average | ❌ **MISSING** - Field doesn't exist in academics table |
| **Enquiry Source** | source | enquiries | source | ⚠️ **NO ENQUIRY** - Student has no enquiry record |
| **Interest Level** | interest_level | enquiries | interest_level | ❌ **MISSING** - Field doesn't exist in enquiries table |
| **Preferred Dept** | preferred_dept_id | admissions | preferred_dept_id | ⚠️ **NO ADMISSION** - Student has no admission record |
| **Allotted Dept** | allotted_dept_id | admissions | allotted_dept_id | ⚠️ **NO ADMISSION** - Student has no admission record |
| **Quota Type** | quota_type | admissions | quota_type | ❌ **MISSING** - Field doesn't exist in admissions table |
| **App Status** | status | admission_applications | status | ⚠️ **NULL** - Application might not have status |
| **Docs Count** | documents_count | admission_applications | documents_count | ❌ **MISSING** - Field doesn't exist |

---

## Issues Identified

### 1. **Fields That Don't Exist in Database Schema**

These fields are being queried but don't exist in the actual database tables:

#### In `academics` table:
- ❌ `tnea_eligible` - NOT IN SCHEMA
- ❌ `tnea_average` - NOT IN SCHEMA

**What exists instead:**
```sql
-- From schema.sql
CREATE TABLE academic_details (
    academic_id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    school_name VARCHAR(200),
    board VARCHAR(50),
    exam_year INTEGER,
    maths_marks NUMERIC(5,2),
    physics_marks NUMERIC(5,2),
    chemistry_marks NUMERIC(5,2),
    total_marks NUMERIC(6,2),
    percentage NUMERIC(5,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### In `enquiries` table:
- ❌ `interest_level` - NOT IN SCHEMA

**What exists instead:**
```sql
CREATE TABLE enquiries (
    enquiry_id SERIAL PRIMARY KEY,
    student_id INTEGER,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    query_subject TEXT,
    query_description TEXT,
    status VARCHAR(50),
    assigned_to INTEGER,
    response TEXT,
    responded_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### In `admissions` table:
- ❌ `quota_type` - NOT IN SCHEMA

**What exists instead:**
```sql
CREATE TABLE admissions (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT,
    preferred_dept_id BIGINT,
    optional_dept_id TEXT,
    status VARCHAR(50),
    allotted_dept_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### In `admission_applications` table:
- ❌ `documents_count` - NOT IN SCHEMA

**What exists instead:**
```sql
CREATE TABLE admission_applications (
    app_id SERIAL PRIMARY KEY,
    student_id INTEGER,
    registration_id VARCHAR(50),
    academic_id INTEGER,
    primary_dept_id INTEGER,
    secondary_dept_id INTEGER,
    cutoff_score NUMERIC(6,2),
    merit_rank INTEGER,
    application_status VARCHAR(50),
    step1_completed BOOLEAN,
    step2_completed BOOLEAN,
    step3_completed BOOLEAN,
    admission_status VARCHAR(50),
    allocated_dept_id INTEGER,
    allocated_category VARCHAR(20),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 2. **Tables Missing or Not Populated**

The following tables may not have data for this student:

| Table | Purpose | Reason for N/A |
|-------|---------|---|
| **enquiries** | Initial enquiry source | ⚠️ Student may not have made an enquiry (no enquiry_id) |
| **admissions** | Department selection | ⚠️ Student may not be at branch selection stage |
| **counselling_records** | Counselling allocation | ⚠️ No data if student hasn't completed counselling |
| **payments** | Payment records | ⚠️ No data if student hasn't made payment |

---

## Root Cause Analysis

### Why so many N/A values?

1. **Template querying non-existent fields**
   - `hsc_school_name` ← should be `school_name`
   - `hsc_percentage` ← should be `percentage`
   - `tnea_eligible`, `tnea_average` ← don't exist in schema
   - `interest_level` ← doesn't exist in enquiries

2. **Student at early stage of admission process**
   - Only filled up initial details (students table)
   - Has NOT yet:
     - Created an enquiry record
     - Selected departments (no admissions record)
     - Submitted complete application
     - Gone through counselling
     - Made payment

3. **Field name mismatches in route.py**
   - Route code references field names that don't match actual database columns

---

## Solution Steps

### STEP 1: Fix Field Names in Template
Update [student_profiles.html](templates/admin/student_profiles.html) to use correct field names:

```diff
- {{ data.academic.hsc_school_name or 'N/A' }}
+ {{ data.academic.school_name or 'N/A' }}

- {{ data.academic.hsc_percentage or 'N/A' }}
+ {{ data.academic.percentage or 'N/A' }}

- {{ data.academic.tnea_eligible or 'N/A' }}
+ (Remove - field doesn't exist)

- {{ data.academic.tnea_average or 'N/A' }}
+ (Remove - field doesn't exist)

- {{ enq.interest_level or 'N/A' }}
+ (Remove - field doesn't exist in enquiries)
```

### STEP 2: Add Missing Database Columns (Optional Enhancement)

If you want to track TNEA-related data, add to `academics` table:

```sql
ALTER TABLE public.academics
ADD COLUMN IF NOT EXISTS tnea_eligible BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS tnea_average NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS tnea_rank INTEGER;
```

If you want to track interest level in enquiries:

```sql
ALTER TABLE public.enquiries
ADD COLUMN IF NOT EXISTS interest_level VARCHAR(50) DEFAULT 'not_specified';
```

If you want quota type in admissions:

```sql
ALTER TABLE public.admissions
ADD COLUMN IF NOT EXISTS quota_type VARCHAR(50);
```

### STEP 3: Add Missing Columns to admission_applications

```sql
ALTER TABLE public.admission_applications
ADD COLUMN IF NOT EXISTS documents_count INTEGER DEFAULT 0;
```

### STEP 4: Update student_profiles() Route

Fix field references to match actual database schema:

```python
# In admin/routes.py, student_profiles() function
# Change from:
<td>{{ data.academic.hsc_school_name or 'N/A' }}</td>

# To:
<td>{{ data.academic.school_name or 'N/A' }}</td>
```

---

## Testing for Student PMC25000126

To debug why this student shows N/A, check database directly:

```python
# In Python shell or script
from database.supabase_config import db

# Check student exists
student = db.select('students', filters={'id': 'PMC25000126'})
print("Student:", student)

# Check academics record
academics = db.select('academics', filters={'student_id': student[0]['student_id']})
print("Academics:", academics)

# Check enquiries
enquiries = db.select('enquiries', filters={'student_id': student[0]['student_id']})
print("Enquiries:", enquiries)

# Check admissions
admissions = db.select('admissions', filters={'student_id': student[0]['student_id']})
print("Admissions:", admissions)

# Check applications
applications = db.select('admission_applications', filters={'student_id': student[0]['student_id']})
print("Applications:", applications)
```

---

## Summary

**The main issues are:**

1. ❌ **Template uses wrong field names** (e.g., `hsc_school_name` instead of `school_name`)
2. ❌ **Template queries non-existent fields** (e.g., `tnea_eligible`, `interest_level`)
3. ⚠️ **Student hasn't progressed through full admission workflow** - only has basic student info
4. ⚠️ **Missing data in related tables** - no enquiry, admission, counselling, or payment records

**Recommended Fix Priority:**

1. **HIGH**: Fix field name mappings in template (hsc_school_name → school_name, etc.)
2. **HIGH**: Remove template fields that don't exist in schema
3. **MEDIUM**: Add missing database columns if needed (TNEA fields, interest_level, quota_type, documents_count)
4. **LOW**: Ensure test data populates all related tables for complete testing
