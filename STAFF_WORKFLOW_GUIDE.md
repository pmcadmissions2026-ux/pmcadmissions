# PMC ADMISSION CONTROL SYSTEM
## Staff-Only Admission Management System

### 🚨 IMPORTANT: NO STUDENT PORTAL
This is a **staff-only system**. Students DO NOT have login access. All admission data is entered and managed by authorized staff members only.

---

## System Architecture

### Staff Roles & Responsibilities

| Role | Access Level | Responsibilities |
|------|--------------|------------------|
| **Admission Coordinator** | Step 1 Only | - Receive student enquiries<br>- Enter student personal details<br>- Record academic marks<br>- Calculate cutoff scores |
| **Admin** | Steps 1, 2, 3 | - Access all enquiry steps<br>- Assign departments/branches<br>- Manage seat allocation<br>- Review applications |
| **Super Admin** | All Steps + System | - Final application approval<br>- User/staff management<br>- System configuration<br>- Full access to all features |

---

## 3-Step Admission Workflow

### 📋 Step 1: Enquiry Data Entry
**Role Required:** `admin`

**Staff Action:**
1. Access enquiries list from dashboard
2. Click "Start Admission" on open enquiry
3. Enter student details:
   - Full name, WhatsApp, email
   - Father's & Mother's names
   - 12th school name & board
   - **Marks:** Maths, Physics, Chemistry
   - Religion, community, quota type
4. System auto-calculates cutoff: `Maths + (Physics + Chemistry)/2`
5. Save & proceed to Step 2

**Restrictions:**
- Admin users manage complete workflow
- Data can be edited via Step 3 summary

---

### 🎓 Step 2: Department Allocation
**Role Required:** `admin`

**Staff Action:**
1. View student summary (name, contact, cutoff score)
2. Select **Primary Department** (required)
3. Optionally select **Secondary Department**
4. System validates against:
   - Minimum cutoff requirements
   - Seat availability
   - Department eligibility
5. Save allocation & proceed to Step 3

**Restrictions:**
- Only admin and super_admin roles allowed
- Department changes may require senior approval

---

### ✅ Step 3: Final Review & Submission
**Role Required:** `super_admin` or `admin`

**Staff Action:**
1. Review complete application summary:
   - Personal information
   - Academic records with cutoff
   - Department allocation (primary/secondary)
2. Verify all data accuracy
3. Use "Edit" links if corrections needed
4. Click "Submit Application" for final approval
5. System actions:
   - Marks enquiry as "converted"
   - Creates admission application record
   - Logs submission in audit trail
   - Locks application for review period

**Features:**
- Edit any step via clickable links
- Download PDF summary (coming soon)
- Application status tracking
- Audit trail logging

---

## Enquiry Management

### Creating New Enquiry
**Staff enters enquiry details manually:**

1. Navigate to **Enquiries** section
2. Click "New Enquiry" button
3. Fill basic details:
   - Student name
   - Contact number
   - Preferred course/department
   - Source of enquiry
4. Click "Start Admission" to begin 3-step process

### Enquiry Status Flow
```
Open → In Progress (Step 1) → Branch Selected (Step 2) → Converted (Step 3 Submitted)
```

---

## User Access Control

### Login Credentials (Default)
```
Super Admin:
Email: super_admin@pmc.edu
Password: admin123

Admin (Department Head):
Created by super admin via Staff Management
```

### Creating New Staff Users
**Only Super Admin can create staff:**

1. Go to **Staff Management**
2. Click "Add Staff Member"
3. Fill details:
   - Employee ID
   - Email & password
   - Name & phone
   - **Assign Role:** 
     - `admin` → Full admission workflow
4. Staff receives credentials
5. They login and start their assigned tasks

---

## Key Features

### ✅ Role-Based Workflow
- Different staff for different admission stages
- Prevents unauthorized access to sensitive steps
- Audit trail tracks who did what

### ✅ Data Validation
- Required fields enforcement
- Automatic cutoff calculation
- Department eligibility verification
- Seat availability checking

### ✅ Audit Logging
Every action is logged:
- `enquiry_step1_completed` - Personal details saved
- `enquiry_step2_completed` - Department allocated
- `enquiry_step3_completed` - Application submitted
- Includes: user_id, timestamp, action type

### ✅ Progress Tracking
- Visual progress bars (33%, 66%, 100%)
- Status indicators at each step
- Student summary cards for context

---

## Database Structure

### Core Tables

**enquiries**
- Initial enquiry data
- Source tracking
- Status progression

**students**
- Personal details
- Linked to enquiry_id
- Contact information

**academics**
- School & board details
- Subject marks
- Calculated cutoff score
- Quota type

**admission_applications**
- Primary & secondary departments
- Application status
- Submission timestamp

**audit_log**
- User actions
- Timestamp tracking
- Step completion records

---

## Workflow Example

### Scenario: New Student Enquiry

**Day 1 - Enquiry Staff (Coordinator):**
```
1. Receives walk-in enquiry from "Rajesh Kumar"
2. Creates enquiry record
3. Clicks "Start Admission"
4. Enters: Name, contacts, parents, marks (M:95, P:92, C:88)
5. System calculates cutoff: 95 + (92+88)/2 = 185
6. Saves & progresses to Step 2 (coordinator cannot access)
```

**Day 2 - Department Admin:**
```
1. Views pending enquiry (Rajesh Kumar)
2. Reviews cutoff score (185)
3. Checks department eligibility
4. Assigns: Primary=Computer Science, Secondary=IT
5. Saves allocation
```

**Day 3 - Senior Admin:**
```
1. Reviews complete application
2. Verifies all data
3. Confirms department allocation
4. Clicks "Submit Application"
5. Enquiry converted to active application
6. Student record locked for processing
```

---

## Security Features

### 🔒 No Student Access
- No student login/registration
- No student portal routes
- Staff-managed data entry only

### 🔒 Role Restrictions
- Step 1: Enquiry staff only enter data
- Step 2: Admins only allocate departments
- Step 3: Senior staff only approve

### 🔒 Session Management
- Automatic session expiry
- Role-based redirects
- Unauthorized access blocked

### 🔒 Audit Trail
- All actions logged
- User identification
- Timestamp tracking
- Compliance ready

---

## System Configuration

### Environment Variables (.env)
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SECRET_KEY=your_secret_key
FLASK_ENV=development
```

### Database Connection
- PostgreSQL via Supabase
- SSL encrypted
- Connection pooling
- Error handling

---

## Common Tasks
### Adding New Admin Staff
```
Super Admin → Staff Management → Add Staff
Role: admin
Access: Full admission workflow (all steps)
```

### Viewing Audit Logs
```
Admin Dashboard → Reports → Audit Trail
Filter by: Date, User, Action Type
```

### Bulk Enquiry Import
```
Coming Soon: CSV import for bulk enquiries
```

---

## Troubleshooting

### Issue: Staff can't access next step
**Solution:** Check role assignment. Admission coordinators can only access Step 1.

### Issue: Application won't submit
**Solution:** Verify all required fields in Steps 1 & 2 are completed.

### Issue: Cutoff score wrong
**Solution:** Verify marks formula: Maths + (Physics + Chemistry)/2

---

## System URLs

```
Home/Login:        http://localhost:5000/
Admin Dashboard:   http://localhost:5000/admin/dashboard
Enquiries:         http://localhost:5000/admin/enquiries
Applications:      http://localhost:5000/admin/applications
Staff Management:  http://localhost:5000/admin/staff
```

---

## Support & Contact

For system issues or training:
- Technical Support: IT Department
- User Management: Super Admin
- Process Queries: Academic Head

---

**Last Updated:** January 28, 2026  
**System Version:** 2.0 (Staff-Only Architecture)  
**Database:** Supabase PostgreSQL