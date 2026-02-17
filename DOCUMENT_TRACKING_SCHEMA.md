# Document Upload Table Schema Updates

## Summary
Updated the database schema to properly track document uploads and link documents with admission applications.

## SQL Changes Made

### 1. **admission_applications Table** - Added columns:
```sql
ALTER TABLE public.admission_applications
ADD COLUMN step3_completed BOOLEAN DEFAULT FALSE;
ADD COLUMN documents_count INTEGER DEFAULT 0;
ADD COLUMN documents_submitted_at TIMESTAMP WITH TIME ZONE;
```

### 2. **admissions Table** - Added columns:
```sql
ALTER TABLE public.admissions
ADD COLUMN step3_completed BOOLEAN DEFAULT FALSE;
ADD COLUMN documents_count INTEGER DEFAULT 0;
ADD COLUMN documents_submitted_at TIMESTAMP WITH TIME ZONE;
```

### 3. **documents Table** - Enhanced relationships:
- Foreign key constraint linking to `admission_applications(app_id)`
- Indexes for faster queries

### 4. **Triggers Created**:
- `update_documents_count()` - Auto-updates `admission_applications` when document is inserted
- `sync_admissions_documents()` - Syncs document count between tables

### 5. **View Created**:
`vw_student_documents` - Shows document status with student details

## How It Works

1. **User uploads documents** → Stored in `documents` table
2. **Trigger fires** → Automatically updates `admission_applications.documents_count` and `step3_completed`
3. **Backend syncs** → Updates `admissions` table with same data
4. **Dashboard shows** → Document count and status in the table

## Column Mapping

| Table | Columns Added | Purpose |
|-------|---|---|
| admission_applications | step3_completed, documents_count, documents_submitted_at | Track Step 3 completion |
| admissions | step3_completed, documents_count, documents_submitted_at | Mirror application status |
| documents | Foreign key to app_id | Link documents to applications |

## Backend Updates

**admin/routes.py** - Document upload route now:
- Inserts documents into `documents` table
- Automatically triggers update to `admission_applications` via trigger
- Manually updates `admissions` table for redundancy
- Shows correct document count in success message

## Display Updates

**admin_dashboard.html** - Documents column now:
- Shows ✅ Uploaded badge with count from `documents_count` column
- Shows ⏳ Pending badge if no documents
- Updates in real-time after upload

## SQL Migration File
File: `sql_migrations/update_document_tracking.sql`
- Contains all ALTER TABLE statements
- Contains trigger definitions
- Can be run against Supabase directly

## Testing
1. Upload documents for a student
2. Check `admission_applications` table - `documents_count` should match uploaded files
3. Check `documents` table - Should show all document records with URLs
4. Refresh admin dashboard - Should show "Uploaded (X file(s))" with correct count
