# PMC Admissions — Node.js scaffold

This project scaffolds a minimal Node + Express backend that serves your existing frontend templates and provides simple API routes that proxy to Supabase using a server-side service key.

Quick start

1. Install dependencies

```bash
npm install
```

2. Copy your `.env` file (you already provided one) with at least:

```
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...   # keep this secret
SECRET_KEY=...             # session secret
```

3. Run in development

```bash
npm run dev
```

4. Server routes

- `GET /api/students` - list students (proxied to Supabase)
- `GET /api/admissions` - list admissions
- `POST /api/admissions/:id/assign` - assign a branch (expects `allotted_dept_id` and optional `processed_by` in JSON body)
- `POST /auth/login` - login by email (looks up `staff` table and sets session)
- `POST /auth/logout` - clear session
- `GET /auth/me` - session inspection

Notes & next steps

- This scaffold uses the Supabase service key on the server — never put `SUPABASE_SERVICE_KEY` into client code.
- Add real authentication (Supabase Auth or password checks) before using in production.
- Map additional routes to your `templates/` HTML files as needed.
# PMC ADMISSION CONTROL SYSTEM

## 🚨 Staff-Only Admission Management System

A comprehensive Flask + Supabase application where **authorized staff members** manage the complete student admission workflow. **No student portal** - all data entry and processing performed by administrative personnel.

### System Architecture
- **Step 1:** Enquiry Data Entry (Admission Coordinators only)
- **Step 2:** Department Allocation (Admins only)  
- **Step 3:** Final Review & Submission (Senior Admins)

📖 **[Complete Staff Workflow Guide →](STAFF_WORKFLOW_GUIDE.md)**

---

## 📁 PROJECT STRUCTURE

```
d:\ZEONY\PMC ADMISSION\
│
├── app.py                          # Main Flask application
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (CREATE THIS)
├── SETUP_GUIDE.md                 # Complete setup instructions
├── README.md                      # This file
│
├── database/                      # Database models & configuration
│   ├── __init__.py
│   ├── supabase_config.py        # Supabase connection
│   └── models.py                 # Database models
│
├── auth/                          # Authentication module
│   ├── __init__.py
│   ├── routes.py                 # Login/logout routes
│   └── decorators.py             # RBAC decorators
│
├── admin/                         # Admin routes
│   ├── __init__.py
│   └── routes.py                 # Dashboard, reports, management
│
├── student/                       # Student routes
│   ├── __init__.py
│   └── routes.py                 # Step 1, 2, 3 admission process
│
├── templates/                     # HTML Templates
│   ├── auth/
│   │   ├── login.html            # Login page
│   │   ├── register.html         # Registration (admin)
│   │   └── unauthorized.html     # Access denied
│   ├── admin/
│   │   ├── dashboard.html        # Admin dashboard
│   │   ├── applications.html     # All applications
│   │   ├── view_application.html # Single application detail
│   │   ├── enquiries.html        # Enquiries list
│   │   ├── view_enquiry.html     # Single enquiry
│   │   ├── daily_report.html     # Admission report
│   │   ├── staff_management.html # Staff management
│   │   └── settings.html         # System settings
│   ├── student/
│   │   ├── step1.html            # Personal & academic details
│   │   ├── step2.html            # Branch selection
│   │   ├── step3.html            # Application summary
│   │   ├── application_status.html # Status tracking
│   │   └── enquiry.html          # Enquiry form
│   └── errors/
│       ├── 404.html              # Page not found
│       ├── 500.html              # Server error
│       └── 403.html              # Access denied
│
├── static/                        # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
│
├── sql/
│   └── schema.sql                # Database schema & initial data
│
└── flask_session/                # Session storage (auto-created)
```

---

## 🚀 QUICK START

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase
- Create account at https://supabase.com
- Create new project
- Get API credentials (URL, Key, Service Key)
- Run SQL schema in SQL Editor

### 3. Configure Environment
Create/Edit `.env` file:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_api_key
SUPABASE_SERVICE_KEY=your_service_key
SECRET_KEY=generate_random_key
FLASK_ENV=development
FLASK_DEBUG=True
```

### 4. Run Application
```bash
python app.py
```

### 5. Access Application
- Open browser: **http://localhost:5000**
- Login with: `super_admin@pmc.edu` / `admin123`
- **⚠️ Change password immediately!**

---

## 👥 USER ROLES

| Role | Access | Functions |
|------|--------|-----------|
| **Super Admin** | `/admin/*` | Full system access, staff management |
| **Admin** | `/admin/*` | Applications, reports, enquiries |
| **Admission Coordinator** | `/admin/applications`, `/admin/enquiries` | Process applications, handle enquiries |
| **Student** | `/student/*` | Complete admission steps 1-3 |

---

## 📋 ADMISSION PROCESS

### Step 1: Personal & Academic Details
- Student enters personal information
- Academic marks (Maths, Physics, Chemistry)
- School and board information
- Creates application record

### Step 2: Branch Selection
- Select primary department
- Select secondary department (optional)
- Calculates merit score
- Prepares for final submission

### Step 3: Application Summary
- Review all submitted information
- Final submission
- Generates registration ID
- Application sent for review

---

## 🔧 FEATURES

### Authentication & Authorization
✅ SQL-based user authentication  
✅ Session-based authentication (no JWT required)  
✅ Role-Based Access Control (RBAC)  
✅ Login history tracking  

### Student Management
✅ Multi-step admission form  
✅ Personal details capture  
✅ Academic performance tracking  
✅ Application status tracking  

### Admin Features
✅ Dashboard with statistics  
✅ Application management  
✅ Department allocation  
✅ Enquiry handling  
✅ Daily admission reports  
✅ Staff management  

### Database & Audit
✅ PostgreSQL via Supabase  
✅ Complete audit logging  
✅ Session logging  
✅ Change history tracking  

---

## 📊 DATABASE TABLES

- **roles** - User roles
- **users** - Staff/admin accounts
- **students** - Student records
- **academic_details** - 12th board marks
- **admission_applications** - Application forms
- **enquiries** - Student queries
- **departments** - Engineering departments
- **seats** - Seat allocation per department
- **session_log** - Login tracking
- **audit_log** - Change tracking
- **admission_history** - Status changes
- **documents** - Uploaded documents
- **notifications** - System notifications

---

## 🔒 SECURITY FEATURES

- Plain-text password storage (can be upgraded to bcrypt)
- Session-based authentication
- RBAC with decorators
- SQL injection protection (Supabase ORM)
- Audit logging for compliance
- IP address tracking
- User action logging

---

## 📝 API DOCUMENTATION

### Auth Endpoints
```
POST   /auth/login              Login user
GET    /auth/logout             Logout user
GET    /auth/register           Register new user (Super Admin)
```

### Admin Endpoints
```
GET    /admin/dashboard                    Admin dashboard
GET    /admin/applications                 All applications
GET    /admin/application/<id>             Single application
POST   /admin/application/<id>/allocate    Allocate department
GET    /admin/enquiries                    All enquiries
GET    /admin/enquiry/<id>                 Single enquiry
POST   /admin/enquiry/<id>/update          Update enquiry
GET    /admin/report/daily                 Daily report
GET    /admin/staff                        Staff list
POST   /admin/staff/<id>/toggle            Toggle staff status
```

### Student Endpoints
```
GET    /student/step1                      Admission step 1
POST   /student/step1                      Submit step 1
GET    /student/step2                      Admission step 2
POST   /student/step2                      Submit step 2
GET    /student/step3                      Admission step 3
POST   /student/step3                      Submit step 3
GET    /student/application-status         View status
POST   /student/enquiry                    Create enquiry
```

---

## 🛠️ CONFIGURATION OPTIONS

### Flask Configuration
```python
FLASK_ENV=development|production
FLASK_DEBUG=True|False
SECRET_KEY=your_secret_key
```

### Supabase Configuration
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
```

### Session Configuration
```
SESSION_PERMANENT=False
PERMANENT_SESSION_LIFETIME=3600
SESSION_TYPE=filesystem
```

---

## 📚 TECHNOLOGY STACK

**Backend:**
- Flask 2.3.3
- Python 3.8+
- Supabase (PostgreSQL)

**Frontend:**
- HTML5
- Tailwind CSS
- JavaScript (Vanilla)
- Material Symbols Icons

**Database:**
- PostgreSQL (via Supabase)
- Session Storage (File-based)

**Deployment Ready For:**
- Heroku
- AWS
- Google Cloud
- Azure
- DigitalOcean

---

## 📖 DETAILED DOCUMENTATION

See **SETUP_GUIDE.md** for:
- Step-by-step installation
- Supabase configuration
- Database schema details
- Troubleshooting guide
- Security recommendations

---

## 🐛 TROUBLESHOOTING

### Common Issues

**Connection Error to Supabase:**
```bash
# Check .env file has correct URLs and keys
# Verify Supabase project is active
# Check internet connection
```

**ModuleNotFoundError:**
```bash
pip install -r requirements.txt
```

**Session Not Persisting:**
```bash
# Remove flask_session/ folder
# Restart application
# Clear browser cookies
```

**Login Fails:**
```bash
# Verify user exists in users table
# Check password is correct (plain text)
# Verify user is_active = True
# Check role exists in roles table
```

---

## 📞 SUPPORT

For issues or questions:
1. Review SETUP_GUIDE.md
2. Check troubleshooting section
3. Verify .env configuration
4. Check Supabase console for errors
5. Review Flask console output

---

## 🔄 MAINTENANCE

### Regular Tasks
- Monitor audit logs
- Check session logs
- Backup database regularly
- Update dependencies
- Review security logs

### Recommended Backups
- Daily database backups
- Weekly full backups
- Monthly archive backups

---

## 🎯 ROADMAP (Future Phases)

**Phase 2 - Enhanced Features:**
- Email/SMS notifications
- Document upload system
- PDF report generation
- Bulk import students
- Advanced search filters

**Phase 3 - Improvements:**
- Password hashing (bcrypt)
- Two-factor authentication
- Mobile app
- API rate limiting
- Performance optimization

**Phase 4 - Integration:**
- Payment gateway integration
- Online test platform
- Hostel management
- Alumni portal

---

## ⚖️ LICENSE

© 2025 Er. Perumal Manimekalai College of Engineering  
All rights reserved.

---

## 🎉 GETTING HELP

**Read First:**
- SETUP_GUIDE.md (Complete installation guide)
- This README.md (Overview)
- Code comments (In source files)

**Then Check:**
- Supabase Dashboard (Database status)
- Flask Console (Error messages)
- Browser Console (Client-side errors)

---

## ✅ VERIFICATION CHECKLIST

After setup, verify:
- [ ] All files created in correct locations
- [ ] `.env` file has valid Supabase credentials
- [ ] `requirements.txt` packages installed
- [ ] SQL schema executed in Supabase
- [ ] All 14 tables exist in Supabase
- [ ] Application runs without errors: `python app.py`
- [ ] Can access http://localhost:5000
- [ ] Can login with super_admin@pmc.edu / admin123
- [ ] Admin dashboard loads with statistics
- [ ] All menus and links work correctly

---

**Version:** 1.0.0  
**Last Updated:** January 28, 2026  
**Status:** Production Ready ✅

---

Thank you for using PMC Admission Control System!
