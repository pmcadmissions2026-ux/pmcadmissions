# Multi-Step Admission Process Documentation

## Overview
Integrated 3-step admission process where admin users manage student enquiries through a complete workflow:

### Step 1: Enquiry Form (Personal & Academic Details)
- **Route**: `/admin/enquiries/step1/<enquiry_id>`
- **Required Role**: `admin`
- **Data Collected**:
  - Personal Details: Full name, WhatsApp, email, parents' names
  - Academic: School, board, marks (Maths, Physics, Chemistry)
  - Social: Religion, community, quota type
  - Auto-calculates cutoff score: Math + (Physics + Chemistry)/2

### Step 2: Branch Selection (Department Allocation)
- **Route**: `/admin/enquiries/step2/<enquiry_id>`
- **Required Role**: `admin` (more restricted than Step 1)
- **Data Collected**:
  - Primary Department (required)
  - Secondary Department (optional)
  - Validates against minimum cutoff thresholds

### Step 3: Application Filing Summary (Final Review)
- **Route**: `/admin/enquiries/step3/<enquiry_id>`
- **Required Role**: `super_admin`, `admin`
- **Features**:
  - Displays all collected data from Steps 1 & 2
  - Edit links for each section
  - Final submission with audit logging
  - Marks enquiry as "converted" and application as "submitted"

## Database Integration

### Models Used
- `students` table - Stores student personal details
- `academics` table - Stores academic records with cutoff calculation
- `admission_applications` table - Tracks application progress through steps
- `enquiries` table - Links enquiry to application workflow
- `audit_log` table - Logs all workflow actions

### Key Audit Events
- `enquiry_step1_completed` - When personal/academic details saved
- `enquiry_step2_completed` - When branch selection saved
- `enquiry_step3_completed` - When application submitted

## User Interface

### Enquiries List Enhancement
- Added "Start Admission" button for open enquiries
- Added "Continue" link for in-progress applications
- Maintains existing View action

### Step Templates
All templates built with:
- Tailwind CSS styling matching existing UI
- Progress bars showing completion percentage
- Student summary cards with key information
- Edit buttons for correction/modification
- Form validation with required fields
- Back/Reset/Submit action buttons

## Role-Based Access Control

| Step | Roles | Purpose |
|------|-------|---------|
| Step 1 | admin, super_admin | Collect initial enquiry details |
| Step 2 | admin, super_admin | Branch/department allocation |
| Step 3 | super_admin, admin | Final review and submission |

## Workflow Sequence

```
Open Enquiry
    ↓
[Step 1] Collect Personal & Academic Details (admin_coordinator)
    ↓
[Step 2] Select Primary/Secondary Branches (admin)
    ↓
[Step 3] Final Review & Submission (super_admin/admin)
    ↓
Application Submitted → Enquiry Converted
```

## Function Reference

### Routes in admin/routes.py

1. **enquiry_step1(enquiry_id)**
   - GET: Display form with enquiry data
   - POST: Save student & academic data, redirect to Step 2

2. **enquiry_step2(enquiry_id)**
   - GET: Display department selection form
   - POST: Save branch allocation, redirect to Step 3

3. **enquiry_step3(enquiry_id)**
   - GET: Display final review summary with edit links
   - POST: Submit application, mark as converted

4. **calculate_cutoff(maths, physics, chemistry)**
   - Helper function: Maths + (Physics + Chemistry)/2

## Features

✅ Multi-step form progression with role-based access
✅ Data persistence across steps
✅ Edit functionality at any step (via links in Step 3)
✅ Automatic cutoff score calculation
✅ Audit trail logging for compliance
✅ Progress tracking (33%, 66%, 100%)
✅ Student summary cards
✅ Department availability verification
✅ Final submission with application lock

## Integration Notes

- Works with existing enquiry management system
- Uses current database schema (no new tables required)
- Respects existing role-based access control decorator
- Maintains session and audit logging
- Compatible with existing Flask app structure