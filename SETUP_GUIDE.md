# PMC ADMISSION CONTROL SYSTEM - SETUP GUIDE

## Overview
This is a Flask-based web application for managing college admissions with SQL-based authentication, session management, and role-based access control (RBAC).

---

## TABLE OF CONTENTS
1. [System Architecture](#system-architecture)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Supabase Setup](#supabase-setup)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [User Roles & Permissions](#user-roles--permissions)
8. [Database Schema](#database-schema)
9. [Features Overview](#features-overview)
10. [API Endpoints](#api-endpoints)
11. [Troubleshooting](#troubleshooting)

---

## SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────┐
│           Frontend (Flask Templates)             │
│  (HTML5, Tailwind CSS, JavaScript)              │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│         Flask Application (Backend)              │
│  ├── Auth Routes (Login/Logout)                 │
│  ├── Admin Routes (Dashboard/Reports)           │
│  ├── Student Routes (Admission Steps)           │
│  └── Database Models                            │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│      Supabase PostgreSQL Database               │
│  ├── Users & Authentication                     │
│  ├── Students & Academic Details                │
│  ├── Admission Applications                     │
│  ├── Enquiries Management                       │
│  └── Audit Logs & Session Tracking              │
└─────────────────────────────────────────────────┘
```

---

## PREREQUISITES

- **Python**: 3.8 or higher
- **pip**: Python package manager
- **Supabase Account**: Free tier available at https://supabase.com
- **Web Browser**: Chrome, Firefox, Safari, or Edge
- **Text Editor/IDE**: VS Code, PyCharm, etc.
- **Git** (Optional): For version control

---

## INSTALLATION STEPS

### Step 1: Install Python Dependencies

```bash
cd d:\ZEONY\PMC ADMISSION
pip install -r requirements.txt
```

**Required packages:**
- Flask==2.3.3
- python-dotenv==1.0.0
- supabase==2.3.0
- psycopg2-binary==2.9.7
- flask-session==0.5.0
- Werkzeug==2.3.7

### Step 2: Create Environment Directories

The app automatically creates these directories:
- `flask_session/` - Session storage
- `templates/` - HTML templates
- `static/` - CSS, JS, images

### Step 3: Configure Environment Variables

Edit `.env` file with your Supabase credentials (see Configuration section)

### Step 4: Initialize Supabase Database

Execute the SQL schema in your Supabase project (see Supabase Setup section)

### Step 5: Run the Application

```bash
python app.py
```

The application will run at: **http://localhost:5000**

---

## SUPABASE SETUP

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Click "New Project"
3. Enter project details:
   - **Name**: PMC Admission
   - **Password**: (Strong password)
   - **Region**: Closest to your location
4. Click "Create new project"
5. Wait for initialization (2-3 minutes)

### 2. Get API Credentials

1. Go to **Settings** → **API**
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role** key → `SUPABASE_SERVICE_KEY`

### 3. Execute SQL Schema

1. Go to **SQL Editor**
2. Click **New Query**
3. Copy entire content from `sql/schema.sql`
4. Paste into the SQL editor
5. Click **Run**

### 4. Verify Tables

Go to **Table Editor** and verify these tables exist:
- roles
- users
- departments
- seats
- students
- academic_details
- enquiries
- admission_applications
- admission_history
- audit_log
- session_log
- documents
- notifications
- admission_reports

---

## CONFIGURATION

### Edit `.env` File

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_public_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=change_this_to_a_random_string

# Session Configuration
SESSION_PERMANENT=False
PERMANENT_SESSION_LIFETIME=3600

# Database
DATABASE_SCHEMA=public

# College Information
COLLEGE_NAME=Er. Perumal Manimekalai College of Engineering
COLLEGE_ACRONYM=PMC
ACADEMIC_YEAR=2025-2026
```

### Change Secret Key

Generate a secure secret key:
```bash
python -c "import os; print(os.urandom(24).hex())"
```

---

## RUNNING THE APPLICATION

### Development Mode

```bash
set FLASK_ENV=development
set FLASK_DEBUG=True
python app.py
```

### Production Mode

```bash
set FLASK_ENV=production
set FLASK_DEBUG=False
python app.py
```

### Access the Application

- **URL**: http://localhost:5000
- **Default Admin**: 
  - Email: `super_admin@pmc.edu`
  - Password: `admin123`
  - **⚠️ Change immediately after first login!**

---

## USER ROLES & PERMISSIONS

### 1. Super Admin
- Full system access
- Manage all applications
- View all reports
- Manage staff and roles
- System settings

**Access**: `/admin/*`

### 2. Admin
- Manage applications
- View reports
- Assign departments
- Manage enquiries

**Access**: `/admin/*` (Limited)

### 3. Admission Coordinator
- View applications
- Respond to enquiries
- Track admissions

**Access**: `/admin/applications`, `/admin/enquiries`

### 4. Student
- Complete admission steps (1, 2, 3)
- Submit applications
- Track application status
- Submit enquiries

**Access**: `/student/*`

---

## DATABASE SCHEMA

### Key Tables

#### 1. users
```sql
- user_id (PK)
- employee_id (UNIQUE)
- email (UNIQUE)
- password (PLAIN TEXT)
- first_name, last_name
- role_id (FK -> roles)
- is_active
- last_login
- created_at, updated_at
```

#### 2. students
```sql
- student_id (PK)
- registration_id (UNIQUE)
- full_name, email, phone
- whatsapp_number
- date_of_birth, gender
- community
- father_name, mother_name
- permanent_address, city, state, pincode
- created_at, updated_at
```

#### 3. academic_details
```sql
- academic_id (PK)
- student_id (FK)
- school_name, board
- exam_year
- maths_marks, physics_marks, chemistry_marks
- total_marks, percentage
- created_at, updated_at
```

#### 4. admission_applications
```sql
- app_id (PK)
- student_id (FK)
- registration_id (UNIQUE)
- academic_id (FK)
- primary_dept_id, secondary_dept_id
- cutoff_score, merit_rank
- application_status (step1/step2/step3/submitted)
- step1/2/3_completed (BOOLEAN)
- admission_status (pending/under_review/allocated/rejected)
- allocated_dept_id, allocated_category
- created_at, updated_at
```

#### 5. enquiries
```sql
- enquiry_id (PK)
- student_id (FK)
- full_name, phone, email
- query_subject, query_description
- status (open/in_progress/resolved)
- assigned_to (FK -> users)
- response, responded_at
- created_at, updated_at
```

#### 6. session_log
```sql
- session_id (PK)
- user_id (FK)
- session_start, session_end
- ip_address, user_agent
```

#### 7. audit_log
```sql
- log_id (PK)
- user_id (FK)
- action
- table_name
- record_id
- old_values, new_values (JSONB)
- ip_address
- created_at
```

---

## FEATURES OVERVIEW

### 1. Authentication & Authorization
- ✅ SQL-based user authentication (no hashing)
- ✅ Session-based authentication
- ✅ Role-based access control (RBAC)
- ✅ Login/Logout functionality
- ✅ Session logging

### 2. Student Admission Process
- **Step 1**: Personal & Academic Details
- **Step 2**: Branch Selection (Primary & Secondary)
- **Step 3**: Application Summary & Final Submission

### 3. Admin Dashboard
- Overview statistics
- Application management
- Student enquiry handling
- Daily admission reports
- Staff management

### 4. Admission Reports
- Daily admission status by department
- Seat availability tracking
- Merit-based allocations
- Category-wise admissions

### 5. Enquiry Management
- Create enquiries
- Track enquiry status
- Respond to students
- Assign to coordinators

### 6. Audit Trail
- User login tracking
- Action logging
- Data change history
- IP address logging

---

## API ENDPOINTS

### Authentication Routes
```
GET/POST  /auth/login               - User login
GET       /auth/logout              - User logout
GET/POST  /auth/register            - Register new user (Super Admin only)
GET       /auth/unauthorized        - Unauthorized page
```

### Admin Routes
```
GET       /admin/dashboard          - Admin dashboard
GET       /admin/applications       - View all applications
GET       /admin/application/<id>   - View single application
POST      /admin/application/<id>/allocate - Allocate department
GET       /admin/enquiries          - View enquiries
GET       /admin/enquiry/<id>       - View single enquiry
POST      /admin/enquiry/<id>/update - Update enquiry
GET       /admin/report/daily       - Daily report
GET       /admin/staff              - Staff management
POST      /admin/staff/<id>/toggle  - Toggle staff status
GET       /admin/settings           - System settings
```

### Student Routes
```
GET/POST  /student/step1            - Step 1: Personal details
GET/POST  /student/step2            - Step 2: Branch selection
GET/POST  /student/step3            - Step 3: Application summary
GET       /student/application-status - View application status
GET/POST  /student/enquiry          - Create enquiry
```

### General Routes
```
GET       /                         - Home (redirects based on role)
GET       /health                   - Health check
```

---

## TROUBLESHOOTING

### Issue: "Connection Error - Could not connect to Supabase"

**Solution:**
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Check internet connection
3. Verify Supabase project is active
4. Check Supabase API status

### Issue: "Table does not exist"

**Solution:**
1. Run SQL schema again in Supabase SQL Editor
2. Verify all tables in Table Editor
3. Check database schema is `public`

### Issue: "ModuleNotFoundError: No module named 'supabase'"

**Solution:**
```bash
pip install supabase==2.3.0
```

### Issue: "Session not persisting"

**Solution:**
1. Check `flask_session/` directory exists
2. Clear browser cookies
3. Restart Flask application
4. Check `PERMANENT_SESSION_LIFETIME` in `.env`

### Issue: "Login fails with correct credentials"

**Solution:**
1. Check user `is_active` is True in database
2. Verify password is stored in plain text
3. Check user role exists in `roles` table
4. Verify role_id is correct in `users` table

### Issue: "Permission Denied - Not authorized"

**Solution:**
1. Check user role in session
2. Verify user has required permissions
3. Check role_id in users table
4. Test with different user role

---

## NEXT STEPS

### Phase 2 - Additional Features (Coming Soon)

- [ ] Email notifications
- [ ] SMS notifications
- [ ] Document upload system
- [ ] Batch processing
- [ ] Advanced reporting
- [ ] Student payment integration
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Data export (Excel/PDF)

### Phase 3 - Improvements

- [ ] Password hashing (bcrypt)
- [ ] Two-factor authentication
- [ ] Email verification
- [ ] Forgot password recovery
- [ ] API rate limiting
- [ ] Data backup automation
- [ ] Performance optimization

---

## SUPPORT & DOCUMENTATION

For more help:
1. Check this guide thoroughly
2. Review Supabase documentation: https://supabase.com/docs
3. Flask documentation: https://flask.palletsprojects.com
4. Contact technical support

---

## SECURITY NOTES

⚠️ **Important Security Measures:**

1. **Change Default Password**: Change `super_admin@pmc.edu` password immediately
2. **Use HTTPS**: Enable SSL/TLS in production
3. **Secret Key**: Generate and use strong secret key
4. **Database**: Restrict Supabase access by IP in production
5. **Backups**: Regular database backups
6. **Monitoring**: Monitor audit logs regularly
7. **Updates**: Keep dependencies updated

---

## VERSION INFORMATION

- **Application Version**: 1.0.0
- **Python Version**: 3.8+
- **Flask Version**: 2.3.3
- **Last Updated**: January 28, 2026

---

## LICENSE & COPYRIGHT

© 2025 Er. Perumal Manimekalai College of Engineering
All rights reserved.

---

## QUICK REFERENCE

| Action | Command |
|--------|---------|
| Install dependencies | `pip install -r requirements.txt` |
| Run application | `python app.py` |
| View logs | Check console output |
| Access database | Supabase dashboard |
| Default login | super_admin@pmc.edu / admin123 |
| Health check | GET /health |

---

**Questions? Check this guide first, then contact support.**
