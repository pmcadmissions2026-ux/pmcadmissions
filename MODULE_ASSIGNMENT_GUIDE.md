# Module/Work Assignment System - Implementation Guide

## Overview
A module assignment system has been implemented to allow Super Admins to assign specific modules/work areas to staff members. Only assigned modules will be visible and accessible to that admin.

## System Modules
The following modules are available for assignment:

1. **Dashboard Access** - Access to the main admin dashboard
2. **Enquiry Management** - Handle student enquiries
3. **Application Management** - Process applications
4. **Counselling Management** - Manage counselling sessions
5. **Payment Management** - Handle payments
6. **Document Management** - Manage documents
7. **Reports & Analytics** - View reports
8. **Staff Management** - Manage staff members

**Note:** Super Admin users automatically have access to all modules and cannot have modules restricted.

## How It Works

### 1. **Database Column**
A new column `assigned_modules` has been added to the `users` table:
- **Type:** JSON array (stored as TEXT)
- **Format:** `["enquiries", "applications", "counselling"]`
- **Default:** Empty array for regular admins

### 2. **Staff Management Page**
The staff management interface now shows:
- **New Column:** "Assigned Modules" - displays all modules assigned to each staff member
- Super Admin users show "All Modules"
- Module names are displayed as colored tags

### 3. **Edit Staff Member Page**
When editing a staff member, you can:
- View all available modules as checkboxes
- Select/deselect modules to assign
- Save the assignments
- Module assignments are stored as JSON in the database

### 4. **Access Control**
Module access is enforced via the `check_module_access()` decorator:
- Applied to each route requiring module access
- Automatically checks if user has the required module
- Redirects to dashboard with error message if access denied
- Super Admin bypasses all checks

**Routes Protected:**
- `/admin/enquiries` - Requires 'enquiries' module
- `/admin/enquiries/new` - Requires 'enquiries' module
- `/admin/enquiry/<id>` - Requires 'enquiries' module
- `/admin/applications/list` - Requires 'applications' module
- `/admin/application/<id>` - Requires 'applications' module
- `/admin/counselling` - Requires 'counselling' module
- `/admin/report/daily` - Requires 'reports' module
- `/admin/staff` - Requires 'staff' module

## Implementation Details

### Route Protection Pattern
```python
@admin_bp.route('/enquiries')
@check_module_access('enquiries')  # NEW
@role_required(['super_admin', 'admin'])
def enquiries():
    # Route handler
```

### Module Assignment in Edit Form
```django
<!-- Checkbox for each module -->
<input type="checkbox" name="modules" value="enquiries"
    {% if staff.assigned_modules and 'enquiries' in staff.assigned_modules %}checked{% endif %}/>
```

### Backend Handling
```python
# Get selected modules from form
assigned_modules = request.form.getlist('modules')

# Save as JSON string
'assigned_modules': json.dumps(assigned_modules)

# Parse when reading
if isinstance(assigned_modules, str):
    assigned_modules = json.loads(assigned_modules)
```

## Testing the System

### Test Case 1: Create Admin with Limited Modules
1. Go to Staff Management
2. Create/Edit a staff member
3. Assign only "Enquiry Management" and "Applications Management"
4. Save changes

### Test Case 2: Access Control
1. Login as the limited admin
2. Try to access `/admin/counselling` - Should show error
3. Access `/admin/enquiries` - Should work
4. Access `/admin/applications/list` - Should work

### Test Case 3: Dashboard Display
1. Go to Staff Management
2. Verify the "Assigned Modules" column shows:
   - "All Modules" for Super Admin
   - List of assigned modules as colored tags for regular admins
   - "No modules assigned" if no modules selected

### Test Case 4: Super Admin Bypass
1. Login as Super Admin
2. All modules should be accessible regardless of form settings
3. Check decorator automatically grants access

## Database Migration
If you need to update an existing table without the column:

```sql
ALTER TABLE users ADD COLUMN assigned_modules TEXT DEFAULT '[]';
```

## Files Modified

1. **admin/routes.py**
   - Added `check_module_access()` decorator function
   - Applied decorator to 8+ admin routes
   - Updated edit_staff route to save module assignments
   - Added JSON parsing for assigned_modules

2. **templates/admin/edit_staff.html**
   - Added "Assigned Modules" section
   - Added checkboxes for each module
   - Shows module names with descriptions

3. **templates/admin/staff_management.html**
   - Added "Assigned Modules" column to staff table
   - Shows "All Modules" for Super Admin
   - Shows colored tags for assigned modules
   - Shows "No modules assigned" if empty

## Future Enhancements

1. **Module Groups** - Create module groups (e.g., "Admission Officer", "Counsellor")
2. **Audit Trail** - Log all module access attempts
3. **Module Details** - Show detailed permissions for each module
4. **Bulk Assignment** - Assign modules to multiple staff at once
5. **Role-Based Defaults** - Auto-assign modules based on role

## Error Handling

When a user tries to access a restricted module:
- Flash message appears: "You do not have access to [Module Name] module"
- User is redirected to the dashboard
- Action is logged (if audit logging is implemented)

## Important Notes

⚠️ **Remember:**
- Super Admin users have all modules automatically (cannot be restricted)
- Module assignments are only checked for regular Admin users
- Empty module list means no access to any protected modules
- Module names are case-sensitive in decorators
- JSON format must be valid for parsing

---

**System Status:** ✅ Fully Implemented and Ready to Use
