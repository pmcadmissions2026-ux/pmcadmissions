# INSTALLATION & DEPLOYMENT CHECKLIST

## ✅ PRE-INSTALLATION CHECKLIST

- [ ] Python 3.8+ installed
- [ ] pip (Python package manager) available
- [ ] Supabase account created
- [ ] Internet connection working
- [ ] Administrator access on computer
- [ ] Text editor/IDE available
- [ ] All UI files reviewed and understood

---

## ✅ STEP 1: SUPABASE SETUP (Do First!)

### Create Project
- [ ] Go to https://supabase.com
- [ ] Sign up/Login to account
- [ ] Click "New Project"
- [ ] Enter project name: "PMC Admission"
- [ ] Create strong database password
- [ ] Select region closest to location
- [ ] Click "Create new project"
- [ ] Wait 2-3 minutes for initialization

### Get API Credentials
- [ ] Project fully initialized
- [ ] Go to Settings → API
- [ ] Copy "Project URL" 
- [ ] Copy "anon public" key
- [ ] Copy "service_role" secret key
- [ ] Save credentials in safe place

### Create Database Schema
- [ ] Open SQL Editor in Supabase
- [ ] Click "New Query"
- [ ] Open `sql/schema.sql` from project
- [ ] Copy entire SQL content
- [ ] Paste into SQL editor
- [ ] Click "Run" button
- [ ] Wait for completion (should show "Success")
- [ ] Go to Table Editor
- [ ] Verify all 14 tables exist:
  - [ ] roles
  - [ ] users
  - [ ] students
  - [ ] academic_details
  - [ ] admission_applications
  - [ ] enquiries
  - [ ] departments
  - [ ] seats
  - [ ] session_log
  - [ ] audit_log
  - [ ] admission_history
  - [ ] documents
  - [ ] notifications
  - [ ] admission_reports

### Verify Data
- [ ] Open Table Editor
- [ ] Click on "roles" table
- [ ] Verify 3 roles exist (super_admin, admin, student)
- [ ] Click on "departments" table
- [ ] Verify 12 departments listed
- [ ] Click on "users" table
- [ ] Verify super_admin@pmc.edu user exists

---

## ✅ STEP 2: PROJECT SETUP

### Environment File
- [ ] Open text editor
- [ ] Create new file named `.env`
- [ ] Save in `d:\ZEONY\PMC ADMISSION\` folder
- [ ] Add Supabase URL: `SUPABASE_URL=https://your-project.supabase.co`
- [ ] Add Supabase Key: `SUPABASE_KEY=your_anon_key_here`
- [ ] Add Service Key: `SUPABASE_SERVICE_KEY=your_service_key_here`
- [ ] Add Secret Key: `SECRET_KEY=` (generate random)
- [ ] Add Flask settings:
  - [ ] `FLASK_ENV=development`
  - [ ] `FLASK_DEBUG=True`
- [ ] Save `.env` file
- [ ] Verify file is saved in correct location

### Generate Secret Key (PowerShell)
```powershell
python -c "import os; print(os.urandom(24).hex())"
```
- [ ] Copy the output
- [ ] Paste into `.env` as `SECRET_KEY=`

---

## ✅ STEP 3: INSTALL PYTHON PACKAGES

### Install Dependencies
```powershell
cd d:\ZEONY\PMC ADMISSION
pip install -r requirements.txt
```

Verify installations:
```powershell
pip list
```

Check installed:
- [ ] Flask==2.3.3
- [ ] python-dotenv==1.0.0
- [ ] supabase==2.3.0
- [ ] psycopg2-binary==2.9.7
- [ ] flask-session==0.5.0
- [ ] Werkzeug==2.3.7

---

## ✅ STEP 4: TEST CONNECTION

### Test Supabase Connection
Create file `test_connection.py`:
```python
import os
from dotenv import load_dotenv
from database.supabase_config import db

load_dotenv()

try:
    # Test connection
    roles = db.select('roles')
    print("✅ Supabase Connection: SUCCESS")
    print(f"Roles found: {len(roles)}")
    
    users = db.select('users')
    print(f"Users found: {len(users)}")
    
except Exception as e:
    print("❌ Supabase Connection: FAILED")
    print(f"Error: {str(e)}")
```

Run test:
```powershell
python test_connection.py
```

Result should show:
- [ ] "✅ Supabase Connection: SUCCESS"
- [ ] "Roles found: 4"
- [ ] "Users found: 1"

If failed, check:
- [ ] `.env` file has correct URLs
- [ ] Supabase project is running
- [ ] Internet connection working
- [ ] SQL schema was executed

---

## ✅ STEP 5: START APPLICATION

### Run Flask App
```powershell
cd d:\ZEONY\PMC ADMISSION
python app.py
```

Expected output:
```
 * Running on http://localhost:5000
 * Press CTRL+C to quit
```

- [ ] Application starts without errors
- [ ] Console shows "Running on http://localhost:5000"
- [ ] No error messages displayed

---

## ✅ STEP 6: VERIFY IN BROWSER

### Access Application
- [ ] Open web browser (Chrome, Firefox, etc.)
- [ ] Go to: **http://localhost:5000**
- [ ] Should see login page
- [ ] PMC Admission Portal logo visible
- [ ] "Staff Login" heading visible
- [ ] Login form displays correctly

### Test Login
- [ ] Email: `super_admin@pmc.edu`
- [ ] Password: `admin123`
- [ ] Click "Secure Login"
- [ ] Should redirect to dashboard
- [ ] Admin dashboard displays
- [ ] Shows statistics cards
- [ ] Navigation menu visible

---

## ✅ STEP 7: VERIFY FEATURES

### Dashboard Verification
- [ ] Total Applications card shows "0"
- [ ] Total Students card shows "0"
- [ ] Total Enquiries card shows "0"
- [ ] Open Enquiries card shows "0"
- [ ] Dashboard statistics section visible
- [ ] Quick Actions visible

### Navigation Testing
- [ ] Click "Applications" → Applications list page
- [ ] Click "Enquiries" → Enquiries list page
- [ ] Click "Daily Report" → Report page loads
- [ ] Click "Staff" → Staff management page
- [ ] Click "Settings" → Settings page

### Role Testing
- [ ] Logout (click logout button)
- [ ] Verify session cleared
- [ ] Redirected to login page
- [ ] Try accessing `/admin/dashboard` directly
- [ ] Should redirect to login

---

## ✅ STEP 8: CREATE TEST STUDENT ACCOUNT

### Manual SQL Query (Optional)
Go to Supabase SQL Editor and run:
```sql
INSERT INTO users (employee_id, email, password, first_name, last_name, role_id, is_active)
VALUES ('STUD001', 'student@pmc.edu', 'student123', 'Test', 'Student', 4, TRUE);
```

### Test Student Login
- [ ] Go to login page
- [ ] Use email: `student@pmc.edu`
- [ ] Use password: `student123`
- [ ] Click Login
- [ ] Should redirect to `/student/step1`
- [ ] Step 1 form displays
- [ ] Fill form with test data
- [ ] Submit form
- [ ] Should proceed to Step 2

---

## ✅ STEP 9: CHANGE DEFAULT PASSWORD

**CRITICAL: Do this immediately!**

### Login as Super Admin
- [ ] Login with `super_admin@pmc.edu` / `admin123`
- [ ] Go to Dashboard

### Update Password (Currently Manual)
Go to Supabase → Table Editor → users:
- [ ] Find "super_admin@pmc.edu" row
- [ ] Edit password field
- [ ] Change from "admin123" to strong password
- [ ] Save changes
- [ ] Logout
- [ ] Try login with new password
- [ ] Verify new password works
- [ ] Verify old password doesn't work

---

## ✅ STEP 10: FINAL VERIFICATION

### Complete Functionality Test

#### Authentication
- [ ] Login works
- [ ] Logout works
- [ ] Sessions persist across page refresh
- [ ] Invalid credentials rejected
- [ ] Unauthorized access blocked

#### Admin Features
- [ ] Dashboard loads
- [ ] Applications list works
- [ ] Application detail page works
- [ ] Enquiries list works
- [ ] Daily report generates
- [ ] Staff management accessible

#### Student Features
- [ ] Step 1 form submits
- [ ] Step 2 branch selection works
- [ ] Step 3 application summary displays
- [ ] Application status page works
- [ ] Enquiry form submits

#### Database
- [ ] Data persists after logout/login
- [ ] New records created successfully
- [ ] Records updated correctly
- [ ] Audit logs created

---

## ✅ DEPLOYMENT PREPARATION

### Before Going Live

- [ ] Change all default passwords
- [ ] Generate secure SECRET_KEY
- [ ] Set FLASK_DEBUG=False
- [ ] Set FLASK_ENV=production
- [ ] Review audit logs
- [ ] Backup database
- [ ] Test all admin functions
- [ ] Test all student functions
- [ ] Document access procedures
- [ ] Create user manual
- [ ] Train staff on system
- [ ] Prepare support contacts

---

## 🔧 TROUBLESHOOTING DURING SETUP

### Problem: "ModuleNotFoundError: No module named 'supabase'"
```powershell
pip install supabase==2.3.0
```

### Problem: "Connection refused" to Supabase
- [ ] Check .env has correct URL and keys
- [ ] Verify Supabase project running
- [ ] Check internet connection
- [ ] Run: `python test_connection.py`

### Problem: "No such table" error
- [ ] Go to Supabase SQL Editor
- [ ] Run schema.sql again
- [ ] Verify in Table Editor all 14 tables exist
- [ ] Clear Python cache: `py -m pip cache purge`
- [ ] Restart Flask application

### Problem: Login page loads but login fails
- [ ] Check user exists in Supabase → users table
- [ ] Verify password is plain text (not hashed)
- [ ] Check user is_active = true
- [ ] Verify role_id exists in roles table
- [ ] Check browser console for errors (F12)

### Problem: CSS/Styling looks broken
- [ ] This is normal - Tailwind CSS loads from CDN
- [ ] Requires internet connection
- [ ] Check browser console for Tailwind CDN errors
- [ ] May take 5-10 seconds to load first time

### Problem: Application crashes on startup
```powershell
# Check Python version
python --version

# Check for syntax errors
python -m py_compile app.py

# Run with detailed output
python app.py --debug
```

---

## 📞 GETTING HELP

### Check These First
1. **SETUP_GUIDE.md** - Comprehensive guide
2. **README.md** - Project overview
3. **Code comments** - In source files
4. **Supabase docs** - https://supabase.com/docs
5. **Flask docs** - https://flask.palletsprojects.com

### Information to Have Ready
- Python version
- Error message (full text)
- Last successful step
- .env file content (without sensitive keys)
- Supabase project status
- Browser console errors (F12)

---

## ✅ SETUP COMPLETE!

If you've checked all items above, your system is ready!

### Next Steps:
1. Read user documentation
2. Create staff accounts
3. Train users
4. Start taking admissions
5. Monitor system regularly
6. Keep backups updated

---

**Setup Status:** ✅ **COMPLETE**  
**Ready for Production:** Yes  
**Support Available:** Yes  

---

*For issues, refer to SETUP_GUIDE.md Troubleshooting section*
