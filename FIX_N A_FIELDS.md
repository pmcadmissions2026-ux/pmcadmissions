# Student Profile N/A Fields - ROOT CAUSE & FIX

## DIAGNOSIS COMPLETE

### What I Found:

**The data IS in the database!** The issue is that the template is querying **WRONG FIELD NAMES**.

---

## Actual Data for Student PMC25000126:

### ✅ ACADEMICS TABLE (table: `academics`)
```
Fields available:
- id: 6
- student_id: 6
- school_name: "VMHSS"                    [Used as 'hsc_school_name' in template - WRONG!]
- board: "State Board"
- maths_marks: 69.0
- physics_marks: 83.0
- chemistry_marks: 83.0
- cutoff: 152.0
- quota_type: "Government Quota (GQ)"
- govt_school: true
- first_graduate: true
- exam_year: null
- tnea_average: null                      [Field EXISTS but is NULL]
- tnea_eligible: null                     [Field EXISTS but is NULL]
```

### ✅ ENQUIRIES TABLE
```
Fields available:
- id: 5
- student_id: 6
- source: "staff-entry"
- status: "open"
- student_name, email, whatsapp_number
```

### ✅ ADMISSIONS TABLE
```
Fields available:
- id: 4
- student_id: 6
- preferred_dept_id: 1
- optional_dept_ids: ["3", "4", "5"]
- status: "branch_selection_pending"
- allotted_dept_id: null               [No allotment yet - this is why "N/A"]
```

### ✅ ADMISSION_APPLICATIONS TABLE
```
Documents already added: documents_count column EXISTS
```

### ✅ COUNSELLING_RECORDS TABLE
```
Fields available:
- quota_type: "GQ"
- allotted_dept_id: 1
- allotment_order_number: "76767888"
- consortium_number: null              [Null but field exists]
```

### ✅ PAYMENTS TABLE
```
Fields available:
- amount: 3000.0
- mode_of_payment: "Cash"
- bill_no: "1212121"
```

---

## THE ACTUAL PROBLEM - FIELD NAME MISMATCHES

### In Template `student_profiles.html`:

| Template Code | Database Field | Status |
|---|---|---|
| `data.academic.hsc_school_name` | `data.academic.school_name` | **WRONG - Should be `school_name`** |
| `data.academic.hsc_percentage` | `data.academic.???` | **MISSING FIELD** (use `plus2_percentage` from students table) |
| `data.academic.cutoff` | `data.academic.cutoff` | ✅ CORRECT |
| `data.academic.tnea_eligible` | `data.academic.tnea_eligible` | ✅ Field EXISTS but NULL |
| `data.academic.tnea_average` | `data.academic.tnea_average` | ✅ Field EXISTS but NULL |
| `enq.interest_level` | **DOESN'T EXIST** | ❌ Field doesn't exist in enquiries |

### In student_profiles() route:

The route returns data with table name `'academics'` but template wrongly references field names from old schema.

---

## FIX #1: Update Template Field Names

Update [student_profiles.html](templates/admin/student_profiles.html) lines 97-101:

```diff
- <td class="px-3 py-3 text-xs">{{ data.academic.hsc_school_name or 'N/A' }}</td>
+ <td class="px-3 py-3 text-xs">{{ data.academic.school_name or 'N/A' }}</td>

- <td class="px-3 py-3 text-xs">{{ data.academic.hsc_percentage or 'N/A' }}</td>
+ <td class="px-3 py-3 text-xs">{{ data.student.plus2_percentage or 'N/A' }}</td>

- <td class="px-3 py-3 text-xs font-bold">{{ data.academic.cutoff or 'N/A' }}</td>
+ <td class="px-3 py-3 text-xs font-bold">{{ data.academic.cutoff or 'N/A' }}</td>

- <td class="px-3 py-3 text-xs">{{ data.academic.tnea_eligible or 'N/A' }}</td>
+ <td class="px-3 py-3 text-xs">{{ data.academic.tnea_eligible or 'N/A' }}</td>

- <td class="px-3 py-3 text-xs">{{ data.academic.tnea_average or 'N/A' }}</td>
+ <td class="px-3 py-3 text-xs">{{ data.academic.tnea_average or 'N/A' }}</td>
```

### Remove Non-Existent "Interest Level" Column

The enquiries table doesn't have an `interest_level` field. Either:
- **Option A**: Remove this column from template
- **Option B**: Add the column to enquiries table if you want to track it

---

## FIX #2: Update PDF Template

The PDF template also has the same issues. Update [student_profile_pdf.html](templates/admin/student_profile_pdf.html):

```diff
- {{ profile.academic.hsc_school_name or 'N/A' }}
+ {{ profile.academic.school_name or 'N/A' }}

- {{ profile.academic.hsc_percentage or 'N/A' }}
+ {{ profile.student.plus2_percentage or 'N/A' }}
```

---

## FIX #3 (Optional): Add Missing Fields to Enquiries Table

If you want to track interest level, add to enquiries table:

```sql
ALTER TABLE public.enquiries
ADD COLUMN IF NOT EXISTS interest_level VARCHAR(50) DEFAULT 'not_specified';
```

Then update template to use:
```django-html
{{ enq.interest_level or 'N/A' }}
```

---

## WHY THERE ARE N/A VALUES

Now looking at the actual data:

1. **TNEA fields show N/A**: 
   - `tnea_eligible`: null (not filled in yet)
   - `tnea_average`: null (not filled in yet)
   - These are optional fields

2. **Allotted Dept shows N/A**:
   - `admissions.allotted_dept_id`: null (student hasn't gone through counselling allocation yet)
   - This is expected - student is at "branch_selection_pending" stage

3. **Consortium # shows N/A**:
   - `counselling_records.consortium_number`: null
   - Field exists but wasn't filled in

4. **All other fields have data**: School, cutoff, quota type, etc. are all populated!

---

## THE REAL ISSUE

The template code was written with assumptions about field names that **don't match the actual database schema**.

When Flask renders:
```django-html
{{ data.academic.hsc_school_name }}
```

But the database only has `data.academic.school_name`, Jinja2 returns **empty/None**, which displays as **"N/A"** (per the `or 'N/A'` fallback).

---

## SUMMARY OF REQUIRED CHANGES

### Priority 1 (IMMEDIATE):
1. Change `hsc_school_name` → `school_name` in student_profiles.html
2. Change `hsc_percentage` → `plus2_percentage` (from students table, not academics)

### Priority 2 (HIGH):
3. Update student_profile_pdf.html with same field names
4. Remove `interest_level` column or add it to enquiries table

### Priority 3 (OPTIONAL):
5. If you want TNEA data, populate those fields during student registration
6. If you want consortium #, populate during counselling process
7. If you want allotted dept, must complete counselling allocation

---

## Verified Data Points for PMC25000126:

| Field | Table | Value | Status |
|-------|-------|-------|--------|
| School | academics.school_name | VMHSS | ✅ HAS DATA |
| HSC % | students.plus2_percentage | 90.0 | ✅ HAS DATA |
| Cutoff | academics.cutoff | 152.0 | ✅ HAS DATA |
| TNEA Eligible | academics.tnea_eligible | null | ⚠️ NULL (Optional) |
| TNEA Avg | academics.tnea_average | null | ⚠️ NULL (Optional) |
| Enquiry Source | enquiries.source | staff-entry | ✅ HAS DATA |
| Preferred Dept | admissions.preferred_dept_id | 1 (CSE) | ✅ HAS DATA |
| Allotted Dept | admissions.allotted_dept_id | null | ⚠️ NULL (Not yet allocated) |
| Quota | counselling_records.quota_type | GQ | ✅ HAS DATA |
| Consortium # | counselling_records.consortium_number | null | ⚠️ NULL (Optional) |
| Amount | payments.amount | 3000.0 | ✅ HAS DATA |
