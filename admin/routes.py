from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from auth.decorators import login_required, role_required, get_current_user
from database.models import (
    AdmissionApplicationModel, EnquiryModel, StudentModel,
    DepartmentModel, SeatModel, AcademicModel
)
from database.supabase_config import db
from datetime import datetime, date, timedelta
from config import Config
import json as json_lib
import traceback
import requests

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/debug/sdk-rest-admin')
@role_required(['admin', 'super_admin'])
def debug_sdk_rest_admin():
    """Admin-only debug: compare SDK selects vs REST selects and return JSON.
    Use while logged-in to inspect differences between SDK and REST results.
    """
    info = {
        'env': {
            'supabase_url': (Config.SUPABASE_URL[:60] + '...') if Config.SUPABASE_URL else None,
            'supabase_key_len': len(Config.SUPABASE_KEY) if Config.SUPABASE_KEY else 0,
            'supabase_service_key_len': len(Config.SUPABASE_SERVICE_KEY) if Config.SUPABASE_SERVICE_KEY else 0,
            'secret_key_len': len(Config.SECRET_KEY) if Config.SECRET_KEY else 0,
        }
    }

    sdk_results = {}
    try:
        sdk_results['client_present'] = True if getattr(db, 'client', None) else False
    except Exception:
        sdk_results['client_present'] = False

    try:
        if getattr(db, 'client', None):
            r = db.client.table('students').select('*').limit(5).execute()
            sdk_results['students'] = r.data if r and getattr(r, 'data', None) is not None else []
        else:
            sdk_results['students'] = []
    except Exception as e:
        sdk_results['students_error'] = str(e)
        sdk_results['students'] = []

    try:
        if getattr(db, 'client', None):
            r = db.client.table('admissions').select('*').limit(5).execute()
            sdk_results['admissions'] = r.data if r and getattr(r, 'data', None) is not None else []
        else:
            sdk_results['admissions'] = []
    except Exception as e:
        sdk_results['admissions_error'] = str(e)
        sdk_results['admissions'] = []

    rest_results = {}
    try:
        rest_base = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
        rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
        headers = {'apikey': rest_key, 'Authorization': f'Bearer {rest_key}'} if rest_key else {}
        if rest_base and rest_key:
            s_url = f"{rest_base}/rest/v1/students"
            a_url = f"{rest_base}/rest/v1/admissions"
            s_r = requests.get(s_url, headers=headers, params={'select': '*', 'limit': 5}, timeout=10)
            a_r = requests.get(a_url, headers=headers, params={'select': '*', 'limit': 5}, timeout=10)
            rest_results['students_status'] = s_r.status_code
            try:
                rest_results['students'] = s_r.json() if s_r.status_code == 200 else {'status': s_r.status_code, 'body': s_r.text}
            except Exception:
                rest_results['students'] = {'status': s_r.status_code, 'body': s_r.text}
            rest_results['admissions_status'] = a_r.status_code
            try:
                rest_results['admissions'] = a_r.json() if a_r.status_code == 200 else {'status': a_r.status_code, 'body': a_r.text}
            except Exception:
                rest_results['admissions'] = {'status': a_r.status_code, 'body': a_r.text}
        else:
            rest_results['error'] = 'missing rest_base or rest_key'
    except Exception as e:
        rest_results['error'] = str(e)

    return jsonify({'info': info, 'sdk': sdk_results, 'rest': rest_results})

# Define all admin modules
ADMIN_MODULES = {
    'enquiries': 'Enquiry Management',
    'applications': 'Application Management',
    'branch_selection': 'Branch Selection Management',
    'counselling': 'Counselling Management',
    'payments': 'Payment Management',
    'documents': 'Document Management',
    'reports': 'Reports & Analytics',
    'staff': 'Staff Management',
    'dashboard': 'Dashboard Access'
}

def check_module_access(module_name):
    """Decorator to check if user has access to a specific module"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return redirect(url_for('auth.login'))
            
            # Super admin has access to all modules
            if session.get('user_role') == 'super_admin':
                return f(*args, **kwargs)
            
            # Check assigned modules
            assigned_modules = user.get('assigned_modules')
            if isinstance(assigned_modules, str):
                try:
                    decoded = json_lib.loads(assigned_modules)
                    if isinstance(decoded, str):
                        decoded = json_lib.loads(decoded)
                    assigned_modules = decoded if isinstance(decoded, list) else []
                except:
                    assigned_modules = []
            
            if not assigned_modules or module_name not in assigned_modules:
                flash(f'You do not have access to {ADMIN_MODULES.get(module_name, "this")} module', 'error')
                return redirect(url_for('admin.dashboard'))
            
            return f(*args, **kwargs)
        
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard redirect"""
    user = get_current_user()
    user_role = session.get('user_role')
    
    if not user or not user_role:
        # Clear stale session if user record cannot be found to avoid
        # redirect loops between `/` -> `/admin/dashboard` -> `/auth/login`.
        try:
            session.clear()
        except Exception:
            pass
        return redirect(url_for('auth.login'))
    
    # Redirect based on role
    if user_role == 'super_admin':
        return redirect(url_for('admin.super_admin_dashboard'))
    elif user_role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    else:
        flash('Unauthorized access', 'error')
        return redirect(url_for('auth.login'))


@admin_bp.route('/super-admin')
@role_required(['super_admin'])
def super_admin_dashboard():
    """Super Admin Master Dashboard - Read-only view of all data"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Super Admin'
    
    # Get ALL data from all tables
    all_enquiries = db.select('enquiries') or []
    all_applications = db.select('admission_applications') or []
    all_counselling = db.select('counselling_records') or []
    all_payments = db.select('payments') or []
    all_documents = db.select('documents') or []
    all_students = db.select('students') or []
    all_academics = db.select('academics') or []
    all_admissions = db.select('admissions') or []
    all_users = db.select('users') or []
    all_departments = db.select('departments') or []
    all_audit_logs = db.select('audit_log') or []
    
    # Calculate metrics
    total_enquiries = len(all_enquiries)
    open_enquiries = len([e for e in all_enquiries if e.get('status') == 'open'])
    converted_enquiries = len([e for e in all_enquiries if e.get('status') == 'converted'])
    
    total_applications = len(all_applications)
    approved_applications = len([a for a in all_applications if a.get('status') == 'approved'])
    rejected_applications = len([a for a in all_applications if a.get('status') == 'rejected'])
    
    total_counselled = len(all_counselling)
    total_payments = len(all_payments)
    total_payment_amount = sum([float(p.get('amount', 0) or 0) for p in all_payments])
    
    documents_pending = len([d for d in all_documents if d.get('status') != 'uploaded'])
    documents_uploaded = len([d for d in all_documents if d.get('status') == 'uploaded'])
    
    total_students = len(all_students)
    total_admissions = len(all_admissions)
    total_staff = len(all_users)
    super_admins = len([u for u in all_users if u.get('role_id') == 1])
    active_users = len([u for u in all_users if u.get('is_active')])
    
    total_departments = len(all_departments)
    total_audit_logs = len(all_audit_logs)
    
    # Enrich enquiries with student names
    for enq in all_enquiries:
        student = db.select('students', filters={'id': enq.get('student_id')})
        enq['student_name'] = student[0].get('full_name', 'Unknown') if student else 'Unknown'

    # Build lookup maps for flow views
    student_map = {s.get('id'): s for s in all_students if s.get('id') is not None}
    dept_map = {d.get('id'): d for d in all_departments if d.get('id') is not None}

    def get_student_name(student):
        if not student:
            return 'Unknown'
        name = student.get('full_name')
        if not name:
            first = student.get('first_name', '')
            last = student.get('last_name', '')
            name = f"{first} {last}".strip()
        return name or 'Unknown'

    def get_unique_id(student):
        if not student:
            return 'N/A'
        return student.get('unique_id') or student.get('student_unique_id') or 'N/A'

    # Flow: Enquiry
    flow_enquiries = []
    for enq in all_enquiries:
        student = student_map.get(enq.get('student_id'))
        flow_enquiries.append({
            'enquiry_id': enq.get('id'),
            'student_id': enq.get('student_id'),
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'email': enq.get('email') or (student.get('email') if student else None) or 'N/A',
            'phone': enq.get('phone') or (student.get('phone') if student else None) or 'N/A',
            'status': enq.get('status') or 'N/A',
            'created_at': enq.get('created_at')
        })

    # Build counselling lookup for branch fallback
    counselling_by_student = {}
    for counsel in all_counselling:
        student_id = counsel.get('student_id')
        dept_id = counsel.get('allotted_dept_id') or counsel.get('allotted_department_id') or counsel.get('department_id')
        dept = dept_map.get(dept_id)
        quota = counsel.get('quota_type') or counsel.get('allotted_quota') or counsel.get('quota') or 'N/A'

        if student_id and student_id not in counselling_by_student:
            counselling_by_student[student_id] = {
                'department': dept.get('dept_name') if dept else 'N/A',
                'quota': quota,
                'created_at': counsel.get('created_at')
            }

    # Flow: Branch Selection (Admissions)
    flow_branch = []
    for adm in all_admissions:
        student = student_map.get(adm.get('student_id'))

        preferred_dept_id = adm.get('preferred_dept_id') or adm.get('primary_dept_id')
        preferred_dept = dept_map.get(preferred_dept_id)

        optional_dept_ids = adm.get('optional_dept_ids')
        optional_dept_names = []
        if optional_dept_ids:
            try:
                if isinstance(optional_dept_ids, str):
                    parsed_ids = json_lib.loads(optional_dept_ids)
                elif isinstance(optional_dept_ids, list):
                    parsed_ids = optional_dept_ids
                else:
                    parsed_ids = [optional_dept_ids]
            except Exception:
                parsed_ids = []

            for dept_id in parsed_ids:
                dept = dept_map.get(int(dept_id)) if dept_id is not None else None
                if dept:
                    optional_dept_names.append(dept.get('dept_name') or dept.get('dept_code'))

        allotted_dept_id = adm.get('allotted_dept_id') or adm.get('allocated_dept_id')
        allotted_dept = dept_map.get(allotted_dept_id) if allotted_dept_id else None
        if allotted_dept:
            allotted_dept_name = allotted_dept.get('dept_name')
        else:
            counselling_info = counselling_by_student.get(adm.get('student_id'))
            allotted_dept_name = counselling_info.get('department') if counselling_info else 'N/A'

        student_id = adm.get('student_id')
        counselling_info = counselling_by_student.get(student_id)
        branch_status = adm.get('status') or 'N/A'
        normalized_status = str(branch_status).strip().lower()
        if counselling_info and normalized_status in ['branch_selection_pending', 'pending', 'n/a', 'na', '']:
            branch_status = 'confirmed'

        flow_branch.append({
            'student_id': student_id,
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'preferred_dept': preferred_dept.get('dept_name') if preferred_dept else 'N/A',
            'optional_depts': optional_dept_names,
            'allotted_dept': allotted_dept_name or 'N/A',
            'status': branch_status,
            'created_at': adm.get('created_at')
        })

    # Flow: Document Upload (Applications)
    flow_documents = []
    for app in all_applications:
        student = student_map.get(app.get('student_id'))
        documents_count = app.get('documents_count') or 0
        documents_done = app.get('step3_completed') or documents_count > 0
        application_number = app.get('registration_id') or app.get('application_number') or f"APP-{app.get('app_id')}"

        flow_documents.append({
            'app_id': app.get('app_id') or app.get('id'),
            'application_number': application_number,
            'student_id': app.get('student_id'),
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'documents_count': documents_count,
            'documents_status': 'Completed' if documents_done else 'Pending',
            'submitted_at': app.get('documents_submitted_at') or app.get('created_at')
        })

    # Flow: Document Details (per document)
    app_student_map = {}
    for app in all_applications:
        app_key = app.get('app_id') or app.get('id')
        if app_key is not None:
            app_student_map[app_key] = app.get('student_id')

    flow_document_items = []
    for doc in all_documents:
        app_id = doc.get('application_id') or doc.get('app_id')
        student_id = app_student_map.get(app_id)
        student = student_map.get(student_id)
        flow_document_items.append({
            'document_id': doc.get('id'),
            'application_id': app_id,
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'document_type': doc.get('document_type') or doc.get('doc_type') or 'N/A',
            'status': doc.get('verification_status') or doc.get('status') or 'N/A',
            'uploaded_at': doc.get('created_at')
        })

    # Flow: Counselling
    flow_counselling = []
    for counsel in all_counselling:
        student = student_map.get(counsel.get('student_id'))
        dept_id = counsel.get('allotted_dept_id') or counsel.get('allotted_department_id') or counsel.get('department_id')
        dept = dept_map.get(dept_id)
        quota = counsel.get('quota_type') or counsel.get('allotted_quota') or counsel.get('quota') or 'N/A'

        flow_counselling.append({
            'counselling_id': counsel.get('counselling_id') or counsel.get('id'),
            'student_id': counsel.get('student_id'),
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'department': dept.get('dept_name') if dept else 'N/A',
            'quota': quota,
            'created_at': counsel.get('created_at')
        })

    # Flow: Payments
    flow_payments = []
    for payment in all_payments:
        student = student_map.get(payment.get('student_id'))
        flow_payments.append({
            'payment_id': payment.get('payment_id') or payment.get('id'),
            'app_id': payment.get('app_id'),
            'student_id': payment.get('student_id'),
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'bill_no': payment.get('bill_no') or 'N/A',
            'mode_of_payment': payment.get('mode_of_payment') or 'N/A',
            'amount': payment.get('amount') or 0,
            'created_at': payment.get('created_at')
        })

    # Flow Summary (combined)
    def pick_latest(records):
        latest = {}
        for record in records:
            sid = record.get('student_id')
            if not sid:
                continue
            current = latest.get(sid)
            record_date = record.get('created_at') or record.get('updated_at')
            current_date = current.get('created_at') or current.get('updated_at') if current else None
            if not current:
                latest[sid] = record
            elif record_date and (not current_date or str(record_date) > str(current_date)):
                latest[sid] = record
        return latest

    latest_enquiry = pick_latest(flow_enquiries)
    latest_branch = pick_latest(flow_branch)
    latest_documents = pick_latest(flow_documents)
    latest_counselling = pick_latest(flow_counselling)
    latest_payment = pick_latest(flow_payments)

    all_student_ids = set(student_map.keys())
    all_student_ids.update(latest_enquiry.keys())
    all_student_ids.update(latest_branch.keys())
    all_student_ids.update(latest_documents.keys())
    all_student_ids.update(latest_counselling.keys())
    all_student_ids.update(latest_payment.keys())

    flow_summary = []
    for student_id in sorted(all_student_ids):
        student = student_map.get(student_id)
        enquiry = latest_enquiry.get(student_id)
        branch = latest_branch.get(student_id)
        documents = latest_documents.get(student_id)
        counselling = latest_counselling.get(student_id)
        payment = latest_payment.get(student_id)

        flow_summary.append({
            'student_id': student_id,
            'student_name': get_student_name(student),
            'unique_id': get_unique_id(student),
            'enquiry_status': enquiry.get('status') if enquiry else 'N/A',
            'enquiry_date': enquiry.get('created_at') if enquiry else None,
            'preferred_dept': branch.get('preferred_dept') if branch else 'N/A',
            'allotted_dept': branch.get('allotted_dept') if branch else 'N/A',
            'branch_status': branch.get('status') if branch else 'Pending',
            'documents_status': documents.get('documents_status') if documents else 'Pending',
            'documents_count': documents.get('documents_count') if documents else 0,
            'counselling_date': counselling.get('created_at') if counselling else None,
            'payment_status': payment.get('status') if payment else 'Pending',
            'payment_amount': payment.get('amount') if payment else 0
        })
    
    return render_template('admin/super_admin_dashboard.html',
                          user=user,
                          # Metrics
                          total_enquiries=total_enquiries,
                          open_enquiries=open_enquiries,
                          converted_enquiries=converted_enquiries,
                          total_applications=total_applications,
                          approved_applications=approved_applications,
                          rejected_applications=rejected_applications,
                          total_counselled=total_counselled,
                          total_payments=total_payments,
                          total_payment_amount=total_payment_amount,
                          documents_pending=documents_pending,
                          documents_uploaded=documents_uploaded,
                          total_students=total_students,
                          total_admissions=total_admissions,
                          total_staff=total_staff,
                          super_admins=super_admins,
                          active_users=active_users,
                          total_departments=total_departments,
                          total_audit_logs=total_audit_logs,
                          # Full data lists for viewing
                          all_enquiries=all_enquiries,
                          all_applications=all_applications,
                          all_counselling=all_counselling,
                          all_payments=all_payments,
                          all_documents=all_documents,
                          all_students=all_students,
                          all_academics=all_academics,
                          all_admissions=all_admissions,
                          all_users=all_users,
                          all_departments=all_departments,
                          all_audit_logs=all_audit_logs[:50],  # Last 50 logs
                          # Flow datasets
                          flow_enquiries=flow_enquiries,
                          flow_branch=flow_branch,
                          flow_documents=flow_documents,
                          flow_counselling=flow_counselling,
                          flow_payments=flow_payments,
                          flow_summary=flow_summary,
                          flow_document_items=flow_document_items
                          )


@admin_bp.route('/admission-controller')
@role_required(['admin', 'super_admin'])
def admission_controller_dashboard():
    """Admission Controller Dashboard - Enquiries Management Only"""
    user = get_current_user()
    
    # Add role to user object for template
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    
    # Get all enquiries
    all_enquiries = db.select('enquiries')
    
    # Get today's enquiries count
    today = datetime.now().date()
    today_count = 0
    yesterday_count = 0
    
    if all_enquiries:
        for enq in all_enquiries:
            created_at = enq.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        enq_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    else:
                        enq_date = created_at.date()
                    
                    if enq_date == today:
                        today_count += 1
                    elif enq_date == (today - timedelta(days=1)):
                        yesterday_count += 1
                except:
                    pass
    
    today_percentage = 0
    if yesterday_count > 0:
        today_percentage = round(((today_count - yesterday_count) / yesterday_count) * 100, 1)
    elif today_count > 0:
        today_percentage = 100
    
    # Get pending follow-ups (contacted status)
    pending_followups = len([e for e in all_enquiries if e.get('status') == 'contacted']) if all_enquiries else 0
    
    # Get completed conversions
    completed_conversions = len([e for e in all_enquiries if e.get('status') == 'converted']) if all_enquiries else 0
    
    # Get recent enquiries with academic details
    try:
        enquiries_response = db.client.table('enquiries').select('*').order('created_at', desc=True).limit(10).execute()
        recent_enquiries_data = enquiries_response.data if enquiries_response else []
    except:
        recent_enquiries_data = db.select('enquiries')
        recent_enquiries_data = recent_enquiries_data[:10] if recent_enquiries_data else []
    
    # Enhance with student cutoff data
    recent_enquiries = []
    if recent_enquiries_data:
        for enq in recent_enquiries_data:
            if enq.get('student_id'):
                academic = db.select('academics', 
                                    filters={'student_id': enq['student_id']})
                academic = academic[0] if academic and isinstance(academic, list) and len(academic) > 0 else None
                if academic:
                    enq['cutoff'] = academic.get('cutoff')
            recent_enquiries.append(enq)
    
    total_enquiries = db.count('enquiries')
    
    stats = {
        'today_enquiries': today_count,
        'today_percentage': today_percentage,
        'pending_followups': pending_followups,
        'high_priority': 0,  # Can be calculated based on criteria
        'completed_conversions': completed_conversions,
        'conversion_percentage': 0
    }
    
    return render_template('admin/admission_controller_dashboard.html',
                          user=user,
                          stats=stats,
                          recent_enquiries=recent_enquiries,
                          total_enquiries=total_enquiries,
                          pending_followups=pending_followups)


@admin_bp.route('/admin-branch-management')
@role_required(['admin', 'super_admin'])
@check_module_access('branch_selection')
def admin_dashboard():
    """Admin Dashboard - Branch Assignment Only"""
    user = get_current_user()
    
    # Add role to user object for template
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'
        
        # Parse assigned modules (handle double-encoding)
        assigned_modules = user.get('assigned_modules')
        if isinstance(assigned_modules, str):
            try:
                # First decode
                decoded = json_lib.loads(assigned_modules)
                # If result is still a string, decode again (double-encoded)
                if isinstance(decoded, str):
                    decoded = json_lib.loads(decoded)
                user['assigned_modules'] = decoded if isinstance(decoded, list) else []
                print(f"DEBUG: Parsed modules for {user.get('first_name')}: {user['assigned_modules']}")
            except Exception as parsing_error:
                print(f"DEBUG: Error parsing modules: {str(parsing_error)}")
                user['assigned_modules'] = []
        elif assigned_modules is None:
            user['assigned_modules'] = []
        else:
            print(f"DEBUG: Modules already a list: {assigned_modules}")
    
    # Get students pending branch selection
    # First, get all students using Supabase client directly for ordering and limit
    try:
        students_response = db.client.table('students').select('*').order('created_at', desc=True).limit(100).execute()
        all_students = students_response.data if students_response else []
        try:
            sd = getattr(students_response, 'data', None)
            print(f"DEBUG: students_response present type={type(students_response)} data_present={bool(sd)} count={len(sd) if sd else 0}")
        except Exception:
            print("DEBUG: students_response logging failed")
    except:
        all_students = db.select('students')
        print(f"DEBUG: students_response SDK failed, fallback students count={len(all_students) if all_students else 0}")
    
    # Get all students who already have branch assignments (from admissions table)
    try:
        admissions_response = db.client.table('admissions').select('student_id').execute()
        assigned_student_ids = [adm['student_id'] for adm in admissions_response.data] if admissions_response.data else []
        try:
            ad = getattr(admissions_response, 'data', None)
            print(f"DEBUG: admissions_response present type={type(admissions_response)} data_present={bool(ad)} count={len(ad) if ad else 0}")
        except Exception:
            print("DEBUG: admissions_response logging failed")
    except:
        admissions = db.select('admissions', columns='student_id')
        assigned_student_ids = [adm['student_id'] for adm in admissions] if admissions else []
        print(f"DEBUG: admissions_response SDK failed, fallback admissions count={len(assigned_student_ids) if assigned_student_ids else 0}")
    
    pending_students = []
    if all_students:
        for student in all_students:
            student_id = student.get('id') or student.get('student_id')
            
            # Skip if already has branch assignment
            if student_id in assigned_student_ids:
                continue

            # Skip if student already accepted by an admin
            status_val = (student.get('status') or '').strip().lower()
            if status_val == 'accepted':
                continue
            
            # Get academic details
            academic = db.select('academics', 
                                filters={'student_id': student_id})
            academic = academic[0] if academic and isinstance(academic, list) and len(academic) > 0 else None
            
            # Only include if has cutoff
            if not academic or not academic.get('cutoff'):
                continue
            
            # Get enquiry
            enquiry = db.select('enquiries',
                               filters={'student_id': student_id})
            enquiry = enquiry[0] if enquiry and isinstance(enquiry, list) and len(enquiry) > 0 else None
            
            # Calculate time ago
            created_at = student.get('created_at')
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
                    diff = now - created
                    
                    if diff.days > 0:
                        time_ago = f"{diff.days}d ago"
                    elif diff.seconds > 3600:
                        time_ago = f"{diff.seconds // 3600}h ago"
                    else:
                        time_ago = f"{diff.seconds // 60}m ago"
                except:
                    time_ago = "Recently"
            else:
                time_ago = "Recently"
            
            pending_students.append({
                'student_id': student_id,
                'name': student.get('name') or student.get('full_name', 'N/A'),
                'unique_id': student.get('unique_id'),
                'community': student.get('community'),
                'cutoff': academic.get('cutoff'),
                'enquiry_id': enquiry.get('id') if enquiry else None,
                'time_ago': time_ago
            })
            
            # Limit to 50 results
            if len(pending_students) >= 50:
                break
    
    # Get students with assigned branches
    assigned_students = []
    # current user name for filtering admissions to only those accepted by this admin
    current_user_name = user.get('name') if user else None
    try:
        admissions_response = db.client.table('admissions').select('*').execute()
        admissions_list = admissions_response.data if admissions_response.data else []
        
        for admission in admissions_list:
            student_id = admission.get('student_id')
            
            # Get student details
            student_data = db.select('students', filters={'id': student_id})
            if not student_data or len(student_data) == 0:
                continue
            student = student_data[0]
            # Only include admissions accepted by the current admin
            try:
                accepted_by = (student.get('accepted_by') or '').strip().lower()
            except Exception:
                accepted_by = ''
            # Do not restrict assigned students by the accepting admin name here;
            # show all assigned students (admins have role-based access already).
            # Only include assigned admissions for students who have been accepted
            try:
                student_status = (student.get('status') or '').strip().lower()
            except Exception:
                student_status = ''
            if student_status != 'accepted':
                continue
            
            # Get academic details for cutoff
            academic = db.select('academics', filters={'student_id': student_id})
            academic = academic[0] if academic else None
            
            # Get preferred department details
            pref_dept_id = admission.get('preferred_dept_id')
            pref_dept = db.select('departments', filters={'id': pref_dept_id})
            pref_dept = pref_dept[0] if pref_dept else None
            
            # Get optional departments details (multiple departments as JSON array)
            optional_dept_ids = admission.get('optional_dept_ids')
            optional_depts_list = []
            if optional_dept_ids:
                try:
                    # Parse JSON if it's a string
                    if isinstance(optional_dept_ids, str):
                        dept_ids = json_lib.loads(optional_dept_ids)
                    else:
                        dept_ids = optional_dept_ids
                    
                    # Fetch each department
                    for dept_id in dept_ids:
                        opt_dept_result = db.select('departments', filters={'id': int(dept_id)})
                        if opt_dept_result:
                            optional_depts_list.append(opt_dept_result[0])
                except Exception as e:
                    print(f"Error parsing optional departments: {e}")
            
            # Get allotted department details
            allotted_dept_id = admission.get('allotted_dept_id')
            allotted_dept = None
            if allotted_dept_id:
                allotted_dept_result = db.select('departments', filters={'id': allotted_dept_id})
                allotted_dept = allotted_dept_result[0] if allotted_dept_result else None
            
            # Get document upload status from admission_applications table (not admissions)
            app_id = None
            try:
                admission_app = db.select('admission_applications', filters={'student_id': student_id})
                if admission_app and len(admission_app) > 0:
                    app_data = admission_app[0]
                    app_id = app_data.get('app_id')
                    documents_uploaded = app_data.get('step3_completed', False)
                    documents_count = app_data.get('documents_count', 0)
                    documents_submitted_at = app_data.get('documents_submitted_at')
                else:
                    documents_uploaded = False
                    documents_count = 0
                    documents_submitted_at = None
            except:
                # Fallback to admissions table if admission_applications query fails
                documents_uploaded = admission.get('documents_uploaded', False)
                documents = admission.get('documents', {})
                documents_count = len(documents) if documents and isinstance(documents, dict) else 0
                documents_submitted_at = admission.get('documents_submitted_at')
            
            assigned_students.append({
                'student_id': student_id,
                'app_id': app_id,
                'name': student.get('full_name', 'N/A'),
                'unique_id': student.get('unique_id'),
                'community': student.get('community'),
                'cutoff': academic.get('cutoff') if academic else 0,
                'preferred_dept': pref_dept.get('dept_name') if pref_dept else 'N/A',
                'preferred_dept_code': pref_dept.get('dept_code') if pref_dept else '',
                'optional_depts': optional_depts_list,  # List of department objects
                'allotted_dept': allotted_dept.get('dept_name') if allotted_dept else '-',
                'allotted_dept_code': allotted_dept.get('dept_code') if allotted_dept else '',
                'status': admission.get('status'),
                'assignment_date': admission.get('created_at'),
                'documents_uploaded': documents_uploaded,
                'documents_count': documents_count,
                'documents_submitted_at': documents_submitted_at
            })
    except Exception as e:
        print(f"Error fetching assigned students: {e}")
        assigned_students = []

    # Get all students with status 'accepted' (no admin-based filtering)
    accepted_students = []
    try:
        accepted_rows = []
        # Prefer SDK client; fallback to db.select
        try:
            if getattr(db, 'client', None):
                resp = db.client.table('students').select('*').eq('status', 'accepted').order('accepted_at', desc=True).limit(200).execute()
                accepted_rows = resp.data if resp and getattr(resp, 'data', None) is not None else []
        except Exception:
            accepted_rows = db.select('students', filters={'status': 'accepted'}) or []

        for st in accepted_rows:
            student_id = st.get('id') or st.get('student_id')
            academic = (db.select('academics', filters={'student_id': student_id}) or [])
            academic = academic[0] if academic else None
            enquiry = (db.select('enquiries', filters={'student_id': student_id}) or [])
            enquiry = enquiry[0] if enquiry else None

            accepted_students.append({
                'student_id': student_id,
                'name': st.get('full_name') or st.get('name') or 'N/A',
                'unique_id': st.get('unique_id'),
                'accepted_by': st.get('accepted_by'),
                'accepted_at': st.get('accepted_at'),
                'cutoff': academic.get('cutoff') if academic else None,
                'enquiry_id': enquiry.get('enquiry_id') if enquiry else None,
                'has_admission': True if (db.select('admissions', filters={'student_id': student_id}) or []) else False
            })
    except Exception as e:
        print(f"Error fetching accepted students (simplified): {e}")
        accepted_students = []

    # Build server_debug using direct REST selects with the service key so we can
    # observe what the service-role access returns from the deployed environment.
    server_debug = {}
    try:
        rest_base = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
        rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
        def rest_get(table, extra_params=None):
            if not rest_base or not rest_key:
                return []
            headers = {'apikey': rest_key, 'Authorization': f'Bearer {rest_key}'}
            params = {'select': '*', 'limit': '5'}
            if extra_params:
                params.update(extra_params)
            try:
                url = f"{rest_base}/rest/v1/{table}"
                r = requests.get(url, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    try:
                        return r.json()
                    except Exception:
                        return []
                else:
                    print(f"REST debug select failed {table}: status={r.status_code} body={r.text}")
                    return []
            except Exception as e:
                print(f"REST debug select error for {table}: {e}")
                return []

        server_debug['students_sample'] = rest_get('students')
        server_debug['admissions_sample'] = rest_get('admissions')
        server_debug['accepted_sample'] = rest_get('students', {'status': 'eq.accepted'})
    except Exception as e:
        print(f"Error building server_debug REST samples: {e}")
        server_debug = {'students_sample': [], 'admissions_sample': [], 'accepted_sample': []}

    server_debug['counts'] = {
        'students_count': db.count('students'),
        'admissions_count': db.count('admissions'),
        'accepted_count': db.count('students', filters={'status': 'accepted'})
    }

    return render_template('admin/admin_dashboard.html',
                          user=user,
                          pending_students=pending_students,
                          assigned_students=assigned_students,
                          accepted_students=accepted_students,
                          server_debug=server_debug)


@admin_bp.route('/old-dashboard')
@role_required(['super_admin', 'admin'])
def old_dashboard():
    """Old Admin Dashboard - For Super Admin Only"""
    # Get statistics
    total_applications = db.count('admission_applications')
    total_students = db.count('students')
    total_enquiries = db.count('enquiries')
    open_enquiries = db.count('enquiries', filters={'status': 'open'})
    
    # Get recent applications
    recent_apps = db.select('admission_applications', 
                           filters={}, 
                           columns='*')
    
    # Get admissions by status
    applications = AdmissionApplicationModel.get_all_applications()
    admission_stats = {}
    for app in applications:
        status = app['admission_status']
        admission_stats[status] = admission_stats.get(status, 0) + 1
    
    return render_template('admin/dashboard.html',
                          total_applications=total_applications,
                          total_students=total_students,
                          total_enquiries=total_enquiries,
                          open_enquiries=open_enquiries,
                          admission_stats=admission_stats,
                          college_name=Config.COLLEGE_NAME,
                          academic_year=Config.ACADEMIC_YEAR)

@admin_bp.route('/applications/list')
@check_module_access('applications')
@role_required(['super_admin', 'admin'])
def applications_list():
    """Select student for document upload"""
    user = get_current_user()
    
    try:
        # Get all students who have been assigned branches
        assigned_students = db.select('admissions')
        
        pending_students = []
        completed_students = []
        
        if assigned_students:
            for admission in assigned_students:
                try:
                    student_data = db.select('students', filters={'id': admission['student_id']})
                    if student_data and len(student_data) > 0:
                        student = student_data[0]
                        
                        # Check if documents have been uploaded
                        app_data = db.select('admission_applications', filters={'student_id': admission['student_id']})
                        documents_count = 0
                        app_id = None
                        application_number = None
                        if app_data and len(app_data) > 0:
                            documents_count = app_data[0].get('documents_count', 0)
                            app_id = app_data[0].get('app_id')
                            application_number = app_data[0].get('registration_id') or app_data[0].get('application_number') or f"APP-{app_id}"
                        
                        student_info = {
                            'id': student['id'],
                            'name': student.get('full_name', 'Unknown'),
                            'unique_id': student.get('unique_id', 'N/A'),
                            'documents_count': documents_count,
                            'app_id': app_id,
                            'application_number': application_number
                        }
                        
                        # Separate into pending and completed
                        if documents_count > 0:
                            completed_students.append(student_info)
                        else:
                            pending_students.append(student_info)
                            
                except Exception as e:
                    print(f"Error processing student: {e}")
                    continue
        
        return render_template('admin/select_student.html',
                             user=user,
                             pending_students=pending_students,
                             completed_students=completed_students)
                             
    except Exception as e:
        print(f"Error in applications_list: {e}")
        flash('Error loading students list', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/application/<int:app_id>')
@check_module_access('applications')
@role_required(['super_admin', 'admin'])
def view_application(app_id):
    """View single application details"""
    application = AdmissionApplicationModel.get_application(app_id)
    
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('admin.applications'))
    
    # Get student details
    student = StudentModel.get_student_by_id(application['student_id'])
    academic = AcademicModel.get_academic_details(application['student_id'])
    
    # Get department details
    primary_dept = DepartmentModel.get_department(application['primary_dept_id']) if application['primary_dept_id'] else None
    secondary_dept = DepartmentModel.get_department(application['secondary_dept_id']) if application['secondary_dept_id'] else None
    allocated_dept = DepartmentModel.get_department(application['allocated_dept_id']) if application['allocated_dept_id'] else None
    
    # Get admission history
    history = db.select('admission_history', filters={'app_id': app_id})
    
    return render_template('admin/view_application.html',
                          application=application,
                          student=student,
                          academic=academic,
                          primary_dept=primary_dept,
                          secondary_dept=secondary_dept,
                          allocated_dept=allocated_dept,
                          history=history)


@admin_bp.route('/enquiry/<int:enquiry_id>/details')
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def enquiry_details(enquiry_id):
    """View enquiry details"""
    enquiry = db.select('enquiries', filters={'id': enquiry_id})
    enquiry = enquiry[0] if enquiry and isinstance(enquiry, list) and len(enquiry) > 0 else None
    
    if not enquiry:
        flash('Enquiry not found', 'error')
        return redirect(url_for('admin.enquiries'))
    
    # Get student and academic details if available
    student = None
    academic = None
    if enquiry.get('student_id'):
        student = db.select('students', filters={'id': enquiry['student_id']})
        student = student[0] if student and isinstance(student, list) and len(student) > 0 else None
        academic = db.select('academics', filters={'student_id': enquiry['student_id']})
        academic = academic[0] if academic and isinstance(academic, list) and len(academic) > 0 else None

    # Get related applications and counselling records (if any)
    applications = []
    counselling_records = []
    try:
        # Try by enquiry_id first
        applications = db.select('admission_applications', filters={'enquiry_id': enquiry_id}) or []
        # Fallback: try by student_id
        if not applications and student and student.get('id'):
            applications = db.select('admission_applications', filters={'student_id': student.get('id')}) or []

        # Get counselling records for these applications
        for app in applications:
            app_id = app.get('app_id') or app.get('id')
            if not app_id:
                continue
            recs = db.select('counselling_records', filters={'app_id': app_id}) or []
            for r in recs:
                # attach dept name if available
                if r.get('allotted_dept_id'):
                    dept = db.select('departments', filters={'id': r['allotted_dept_id']})
                    r['dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
                r['app_id'] = app_id
                counselling_records.append(r)
    except Exception:
        applications = applications or []
        counselling_records = counselling_records or []
    
    return render_template('admin/enquiry_details.html',
                          enquiry=enquiry,
                          student=student,
                          academic=academic,
                          applications=applications,
                          counselling_records=counselling_records)


@admin_bp.route('/application/<int:app_id>/allocate', methods=['POST'])
@check_module_access('applications')
@role_required(['super_admin', 'admin'])
def allocate_department(app_id):
    """Allocate department to student"""
    application = AdmissionApplicationModel.get_application(app_id)
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404
    
    dept_id = request.form.get('dept_id')
    category = request.form.get('category')
    
    if not dept_id or not category:
        return jsonify({'success': False, 'message': 'Department and category required'}), 400
    
    try:
        AdmissionApplicationModel.allocate_department(app_id, int(dept_id), category)
        
        # Log in history
        db.insert('admission_history', {
            'app_id': app_id,
            'status_before': application['admission_status'],
            'status_after': 'allocated',
            'changed_by': session.get('user_id'),
            'change_reason': f'Allocated to {DepartmentModel.get_department(int(dept_id))["dept_name"]} - {category}'
        })
        
        flash('Department allocated successfully', 'success')
        return redirect(url_for('admin.view_application', app_id=app_id))
    except Exception as e:
        flash(f'Error allocating department: {str(e)}', 'error')
        return redirect(url_for('admin.view_application', app_id=app_id))

@admin_bp.route('/enquiries')
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def enquiries():
    """View all enquiries"""
    status = request.args.get('status', '')
    
    filters = {'status': status} if status else {}
    enquiries_list = EnquiryModel.get_all_enquiries(filters=filters)

    # Enrich enquiries with TNEA fields and cutoff from academics table when available
    try:
        if enquiries_list:
            for enq in enquiries_list:
                enq['tnea_average'] = None
                enq['tnea_eligible'] = None
                enq['cutoff_score'] = None
                student_id = enq.get('student_id')
                if student_id:
                    acad = db.select('academics', filters={'student_id': student_id})
                    if acad and isinstance(acad, list) and len(acad) > 0:
                        enq['tnea_average'] = acad[0].get('tnea_average')
                        # normalize boolean-like values
                        val = acad[0].get('tnea_eligible')
                        enq['tnea_eligible'] = bool(val) if val is not None else None
                        # cutoff_score stored in academics as 'cutoff_score'
                        try:
                            cs = acad[0].get('cutoff_score')
                            enq['cutoff_score'] = float(cs) if cs is not None else None
                        except:
                            enq['cutoff_score'] = None
    except Exception as e:
        print(f"Error enriching enquiries with academics: {e}")
    
    return render_template('admin/enquiries.html',
                          enquiries=enquiries_list,
                          current_status=status)

@admin_bp.route('/enquiries/new', methods=['GET', 'POST'])
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def new_enquiry():
    """Create new enquiry with complete student details"""
    if request.method == 'POST':
        try:
            # Get personal details
            full_name = request.form.get('full_name')
            plus2_register_number = request.form.get('plus2_register_number')
            whatsapp_number = request.form.get('whatsapp_number')
            email = request.form.get('email')
            father_name = request.form.get('father_name')
            father_phone = request.form.get('father_phone')
            mother_name = request.form.get('mother_name')
            mother_phone = request.form.get('mother_phone')
            date_of_birth = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            aadhar_number = request.form.get('aadhar_number')
            mother_tongue = request.form.get('mother_tongue')
            caste = request.form.get('caste')
            
            # Get 10th standard details
            tenth_school_name = request.form.get('tenth_school_name')
            tenth_marks = request.form.get('tenth_marks')
            tenth_total_marks = request.form.get('tenth_total_marks')
            tenth_percentage = request.form.get('tenth_percentage')
            tenth_year = request.form.get('tenth_year')
            tenth_board = request.form.get('tenth_board')
            tenth_study_state = request.form.get('tenth_study_state')
            tenth_medium_of_study = request.form.get('tenth_medium_of_study')
            
            # Get +2 standard details
            plus2_school_name = request.form.get('plus2_school_name')
            plus2_marks = request.form.get('plus2_marks')
            plus2_total_marks = request.form.get('plus2_total_marks')
            plus2_percentage = request.form.get('plus2_percentage')
            plus2_year = request.form.get('plus2_year')
            
            # Get academic details
            board = request.form.get('board')
            study_state = request.form.get('study_state')
            group_studied = request.form.get('group_studied')
            medium_of_study = request.form.get('medium_of_study')
            maths_marks = request.form.get('maths_marks')
            physics_marks = request.form.get('physics_marks')
            chemistry_marks = request.form.get('chemistry_marks')
            
            # Get social details
            religion = request.form.get('religion')
            community_raw = request.form.get('community')
            community_custom = request.form.get('community_custom')
            general_quota = request.form.get('general_quota')
            category_7_5 = request.form.get('category_7_5') == 'on'
            first_graduate = request.form.get('first_graduate') == 'on'
            reference_details = request.form.get('reference_details')
            
            # Normalize community to allowed list: OC, BC, SC, ST, SCA, BCM. If custom not allowed, set to 'OTHERS'
            allowed = {'OC', 'BC', 'SC', 'ST', 'SCA', 'BCM'}
            community = None
            if community_raw:
                cr = community_raw.strip().upper()
                if cr in allowed:
                    community = cr
                elif cr == 'OTHER' and community_custom:
                    cc = community_custom.strip().upper()
                    community = cc if cc in allowed else 'OTHERS'
                else:
                    community = 'OTHERS'

            # Generate unique_id in format PMC25000126 (PMC + 25 + sequential 4-digit + 26 year)
            student_count = db.count('students')
            next_number = (student_count if student_count else 0) + 1
            unique_id = f"PMC25{next_number:04d}26"  # Format: PMC25000126, PMC25000226, etc.
            
            # Calculate cutoff
            cutoff = 0.0
            if maths_marks and physics_marks and chemistry_marks:
                cutoff = float(maths_marks) + ((float(physics_marks) + float(chemistry_marks)) / 2)

            # Auto-calc percentages if total marks provided and percentage missing
            try:
                if (not tenth_percentage or str(tenth_percentage).strip() == '') and tenth_marks and tenth_total_marks:
                    t_marks = float(tenth_marks)
                    t_total = float(tenth_total_marks)
                    if t_total > 0:
                        tenth_percentage = round((t_marks / t_total) * 100.0, 2)
                if (not plus2_percentage or str(plus2_percentage).strip() == '') and plus2_marks and plus2_total_marks:
                    p_marks = float(plus2_marks)
                    p_total = float(plus2_total_marks)
                    if p_total > 0:
                        plus2_percentage = round((p_marks / p_total) * 100.0, 2)
            except Exception:
                # If conversion fails, ignore and allow later validation to handle
                pass
            
            # Create student record with ONLY columns that exist in the `students` table.
            # This avoids PostgREST/schema-cache errors when the form includes fields
            # that the current DB schema does not have.
            candidate_student = {
                'full_name': full_name,
                'unique_id': unique_id,
                'plus2_register_number': plus2_register_number,
                'emis_number': request.form.get('emis_number') or None,
                'email': email,
                'phone': whatsapp_number,
                'whatsapp_number': whatsapp_number,
                'father_name': father_name,
                'father_phone': father_phone,
                'mother_name': mother_name,
                'mother_phone': mother_phone,
                'religion': religion,
                'community': community,
                'date_of_birth': date_of_birth if date_of_birth else None,
                'gender': gender,
                'aadhar_number': aadhar_number,
                'mother_tongue': mother_tongue,
                'caste': caste,
                'tenth_school_name': tenth_school_name,
                'tenth_marks': float(tenth_marks) if tenth_marks else None,
                'tenth_percentage': float(tenth_percentage) if tenth_percentage else None,
                'tenth_study_state': tenth_study_state or None,
                'tenth_medium_of_study': tenth_medium_of_study or None,
                'tenth_year': int(tenth_year) if tenth_year else None,
                'plus2_school_name': plus2_school_name,
                'plus2_marks': float(plus2_marks) if plus2_marks else None,
                'plus2_percentage': float(plus2_percentage) if plus2_percentage else None,
                'plus2_year': int(plus2_year) if plus2_year else None,
                'board': board,
                'study_state': study_state,
                'group_studied': group_studied,
                'medium_of_study': medium_of_study,
                'general_quota': general_quota,
                'category_7_5': category_7_5,
                'first_graduate': first_graduate,
                'reference_details': reference_details,
                'created_at': datetime.now().isoformat()
            }

            # Determine allowed student columns from the database (sample row)
            try:
                sample_students = db.select('students')
                allowed_student_cols = set(sample_students[0].keys()) if sample_students and isinstance(sample_students, list) and len(sample_students) > 0 else set()
            except Exception:
                allowed_student_cols = set()

            if allowed_student_cols:
                # Use a minimal safe subset of student fields to avoid intermittent PostgREST schema-cache errors.
                minimal_keys = {'full_name', 'unique_id', 'email', 'phone', 'whatsapp_number', 'created_at'}
                # Keep only minimal keys that exist in the DB
                student_data = {k: v for k, v in candidate_student.items() if k in allowed_student_cols and k in minimal_keys}
            else:
                # Fallback: use candidate_student as-is (best-effort)
                student_data = candidate_student

            # If filtering produced an empty payload (schema mismatch), ensure we at least send
            # a minimal payload containing name/email/phone/created_at where available.
            if not student_data:
                minimal_for_insert = {k: candidate_student.get(k) for k in ('full_name', 'email', 'phone', 'whatsapp_number', 'created_at') if candidate_student.get(k) is not None}
                if minimal_for_insert:
                    student_data = minimal_for_insert
                else:
                    raise Exception('Insufficient student data to create record (need at least name, email or phone)')
            
            # Check for existing student by email to avoid duplicate inserts
            student_id = None
            try:
                existing_student = db.select('students', filters={'email': email})
                if existing_student and isinstance(existing_student, list) and len(existing_student) > 0:
                    student_id = existing_student[0].get('id') or existing_student[0].get('student_id')
                    print(f"Dedup: found existing student for email={email} id={student_id}")
                else:
                    student_result = db.insert('students', student_data)
                    if not student_result or not isinstance(student_result, list) or len(student_result) == 0:
                        # Insert returned no body (e.g., REST returned 204) or failed. Try to locate the row
                        # by available unique keys (email, phone, unique_id) in that order.
                        print(f"Student insert returned no result. Trying fallback selects for email/phone/unique_id")
                        try:
                            fallback = None
                            if email:
                                fallback = db.select('students', filters={'email': email})
                            if (not fallback or len(fallback) == 0) and (whatsapp_number or candidate_student.get('phone')):
                                phone_to_check = whatsapp_number or candidate_student.get('phone')
                                fallback = db.select('students', filters={'phone': phone_to_check})
                            if (not fallback or len(fallback) == 0) and candidate_student.get('unique_id'):
                                fallback = db.select('students', filters={'unique_id': candidate_student.get('unique_id')})

                            if fallback and isinstance(fallback, list) and len(fallback) > 0:
                                student_id = fallback[0].get('id') or fallback[0].get('student_id')
                                print(f"Student fallback select found existing row id={student_id}")
                            else:
                                print(f"Student fallback select returned nothing for keys email={email} phone={whatsapp_number} unique_id={candidate_student.get('unique_id')}")
                                raise Exception(f"Failed to create student record. DB returned: {student_result}")
                        except Exception as fe:
                            print(f"Student fallback select error: {fe}")
                            raise Exception(f"Failed to create student record. DB returned: {student_result}")
                    else:
                        student_id = student_result[0].get('id') or student_result[0].get('student_id')
            except Exception as e:
                print(f"Error creating or locating student: {e}")
                raise
            
            # Create academic record with ALL academic details including reservations
            academic_data = {
                'student_id': student_id,
                'school_name': plus2_school_name,
                'board': board,
                'maths_marks': float(maths_marks) if maths_marks else 0,
                'physics_marks': float(physics_marks) if physics_marks else 0,
                'chemistry_marks': float(chemistry_marks) if chemistry_marks else 0,
                'cutoff': cutoff,
                'quota_type': general_quota,
                'govt_school': category_7_5,
                'first_graduate': first_graduate,
                # TNEA eligibility calculation: average of Maths, Physics, Chemistry
                'tnea_average': None,
                'tnea_eligible': False
            }

            # Filter academic_data to allowed columns in academics table if available
            try:
                sample_acad = db.select('academics')
                allowed_acad_cols = set(sample_acad[0].keys()) if sample_acad and isinstance(sample_acad, list) and len(sample_acad) > 0 else set()
            except Exception:
                allowed_acad_cols = set()

            if allowed_acad_cols:
                academic_data = {k: v for k, v in academic_data.items() if k in allowed_acad_cols}
            
            academic_result = db.insert('academics', academic_data)

            if not academic_result:
                # REST may return 204 No Content; try selecting academic record by student_id
                try:
                    acad_fallback = db.select('academics', filters={'student_id': student_id})
                    if acad_fallback and isinstance(acad_fallback, list) and len(acad_fallback) > 0:
                        print(f"Academic fallback select found record for student_id={student_id}")
                        # treat as success
                        academic_result = acad_fallback
                    else:
                        raise Exception("Failed to create academic record")
                except Exception as fe:
                    print(f"Academic fallback select error: {fe}")
                    raise Exception("Failed to create academic record")

            # Calculate TNEA eligibility (average of maths, physics, chemistry)
            try:
                m = float(maths_marks) if maths_marks else 0.0
                p = float(physics_marks) if physics_marks else 0.0
                c = float(chemistry_marks) if chemistry_marks else 0.0
                avg = round((m + p + c) / 3.0, 2)
                threshold = 45.0 if (str(community or '').strip().upper() == 'OC') else 40.0
                eligible = True if avg >= threshold else False
                # update academics record with tnea fields
                try:
                    db.update('academics', {'tnea_average': avg, 'tnea_eligible': eligible}, {'student_id': student_id})
                except Exception:
                    # If update fails, ignore but log
                    print(f"DEBUG: Failed to update TNEA fields for student {student_id}")
            except Exception as e:
                print(f"DEBUG: Failed to compute TNEA eligibility: {e}")
            
            # Create enquiry record
            enquiry_data = {
                'student_name': full_name,
                'whatsapp_number': whatsapp_number,
                'email': email,
                'subject': f'Engineering Admission Enquiry',
                'preferred_course': 'Engineering',
                'source': 'staff-entry',
                'status': 'open',
                'student_id': student_id,
                'created_at': datetime.now().isoformat(),
                'created_by': session.get('user_id')
            }
            
            # Avoid creating duplicate enquiries: if an enquiry for same email+name exists, reuse it
            enquiry_id = None
            try:
                existing_enq = db.select('enquiries', filters={'email': email, 'student_name': full_name})
                if existing_enq and isinstance(existing_enq, list) and len(existing_enq) > 0:
                    enquiry_id = existing_enq[0].get('id')
                    print(f"Dedup: found existing enquiry for email={email} name={full_name} id={enquiry_id}")
                else:
                    enquiry_result = db.insert('enquiries', enquiry_data)
                    if not enquiry_result or not isinstance(enquiry_result, list) or len(enquiry_result) == 0:
                        # Try fallback select (PostgREST may return 204)
                        print(f"Enquiry insert returned no result. Trying fallback select by email+name: {email}, {full_name}")
                        try:
                            enq_fallback = db.select('enquiries', filters={'email': email, 'student_name': full_name})
                            if enq_fallback and isinstance(enq_fallback, list) and len(enq_fallback) > 0:
                                enquiry_id = enq_fallback[0].get('id')
                                print(f"Enquiry fallback select found existing id={enquiry_id}")
                            else:
                                print(f"Enquiry fallback select returned nothing for email/name")
                                raise Exception("Failed to create enquiry record")
                        except Exception as fe:
                            print(f"Enquiry fallback select error: {fe}")
                            raise Exception("Failed to create enquiry record")
                    else:
                        enquiry_id = enquiry_result[0].get('id')
            except Exception as e:
                print(f"Error creating or locating enquiry: {e}")
                raise
            
            # Log action
            db.insert('audit_log', {
                'user_id': session.get('user_id'),
                'action': 'create_enquiry',
                'table_name': 'enquiries',
                'record_id': enquiry_id,
                'new_values': {
                    'student_id': student_id,
                    'full_name': full_name,
                    'email': email,
                    'unique_id': unique_id
                },
                'ip_address': request.remote_addr
            })
            
            flash(f'Enquiry created successfully for {full_name}!', 'success')

            # Instead of redirecting immediately, render the same page with a success_redirect
            # so the UI can show a popup and then navigate. This keeps behavior consistent
            # across serverless environments where immediate redirects may confuse the client.
            success_redirect = url_for('admin.admin_dashboard')

            # Send notification email to student via server-side SMTP/SendGrid (EmailJS removed)
            try:
                from utils.email_helper import send_email_smtp
                from utils.sendgrid_helper import send_email_sendgrid

                subject_line = f"Enquiry Received - {unique_id}"

                html_body = render_template('emails/enquiry.html', full_name=full_name, unique_id=unique_id, subject=enquiry_data.get('subject'), description=request.form.get('reference_details') or '', college_name=Config.COLLEGE_NAME)
                text_body = render_template('emails/enquiry.txt', full_name=full_name, unique_id=unique_id, subject=enquiry_data.get('subject'), description=request.form.get('reference_details') or '', college_name=Config.COLLEGE_NAME)

                to_addr = email
                smtp_sent = send_email_smtp(subject_line, text_body, to_addr, from_name=full_name, reply_to=email, html_body=html_body)
                if smtp_sent:
                    flash('Student saved and notification sent via SMTP.', 'success')
                else:
                    try:
                        sg_sent = send_email_sendgrid(subject_line, text_body, to_addr, from_email=None, from_name=full_name, reply_to=email, html_body=html_body)
                        if sg_sent:
                            flash('Student saved and notification sent via SendGrid fallback.', 'success')
                        else:
                            flash('Student saved but confirmation email failed to send. We will retry.', 'error')
                    except Exception:
                        current_app.logger.exception('SendGrid fallback failed (admin.new_enquiry)')
                        flash('Student saved but confirmation email failed to send. We will retry.', 'error')
            except Exception:
                current_app.logger.exception('Failed to send enquiry email from admin.new_enquiry')
                flash('Student saved but confirmation email failed to send. We will retry.', 'error')

            # Render the form page with a redirect instruction so client shows popup then redirects
            return render_template('admin/new_enquiry.html', success_redirect=success_redirect)
                
        except Exception as e:
            # Capture full traceback for debugging and show on page
            tb = traceback.format_exc()
            current_app.logger.error(tb)
            # Keep the flash for quick notices and also render the page with full debug info
            flash(f'Error creating enquiry: {str(e)}', 'error')
            print(f"Error in new_enquiry: {str(e)}")
            return render_template('admin/new_enquiry.html', debug_error=tb, form_data=request.form)

    return render_template('admin/new_enquiry.html')


@admin_bp.route('/enquiries/check-unique')
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def check_enquiry_unique():
    """API: Check if an enquiry field value already exists (plus2_register_number, email, aadhar_number)."""
    field = request.args.get('field')
    value = request.args.get('value')

    if not field or not value:
        return jsonify({'error': 'field and value are required'}), 400

    allowed = {'plus2_register_number', 'email', 'aadhar_number'}
    if field not in allowed:
        return jsonify({'error': 'invalid field'}), 400

    # Map fields to tables where they are stored. Some fields live in students table.
    field_table_map = {
        'email': ['enquiries', 'students'],
        'plus2_register_number': ['students'],
        'aadhar_number': ['students']
    }

    tables = field_table_map.get(field, [])
    total_matches = 0
    samples = []
    try:
        for tbl in tables:
            try:
                res = db.select(tbl, filters={field: value})
            except Exception:
                # If the column doesn't exist on this table, skip it
                res = None
            if res and isinstance(res, list) and len(res) > 0:
                total_matches += len(res)
                samples.extend(res[:3])

        exists = total_matches > 0
        sample = samples[0] if samples else None
        return jsonify({'exists': exists, 'matched_count': total_matches, 'sample': sample})
    except Exception as e:
        current_app.logger.exception('check_enquiry_unique error')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/debug/supabase-test', methods=['GET', 'POST'])
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def debug_supabase_test():
    """Debug route: try a minimal insert into `students` and show the full response/traceback."""
    debug_error = None
    result = None
    payload = None
    if request.method == 'POST':
        try:
            # Build a minimal payload from form
            full_name = request.form.get('full_name') or f"Debug User {datetime.now().isoformat()}"
            email = request.form.get('email') or f"debug+{int(datetime.now().timestamp())}@example.com"
            phone = request.form.get('phone') or None

            payload = {
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'created_at': datetime.now().isoformat()
            }

            # Attempt insert and capture the raw response
            result = db.insert('students', payload)
            # If db.insert returned None (no result, no exception), attempt a direct REST POST
            rest_response = None
            if result is None:
                try:
                    rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
                    rest_url = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
                    if rest_key and rest_url:
                        headers = {
                            'apikey': rest_key.strip(),
                            'Authorization': f"Bearer {rest_key.strip()}",
                            'Content-Type': 'application/json',
                            'Prefer': 'return=representation'
                        }
                        r = requests.post(f"{rest_url}/rest/v1/students", headers=headers, json=payload, timeout=10)
                        # Capture status, body and headers for debugging (headers may include Content-Range or Location)
                        try:
                            headers_dict = dict(r.headers)
                        except Exception:
                            headers_dict = {}
                        rest_response = {
                            'status_code': r.status_code,
                            'text': r.text,
                            'headers': headers_dict
                        }
                except Exception as e:
                    # capture rest attempt failure
                    rest_response = {'error': str(e)}
            else:
                rest_response = None
        except Exception as e:
            debug_error = traceback.format_exc()
            current_app.logger.error(debug_error)

    return render_template('admin/debug_supabase.html', debug_error=debug_error, result=result, payload=payload, rest_response=rest_response)


# Safe debug route (no decorators) to avoid decorator-side DB calls crashing serverless functions.
# This route verifies a minimal session presence and performs a direct REST POST to Supabase
# using the environment keys. It does NOT use `db` (Supabase SDK) to avoid client initialization.
@admin_bp.route('/debug/safe-supabase-test', methods=['GET', 'POST'])
def debug_safe_supabase_test():
    # Require that a session role be present to reduce accidental public access.
    role = session.get('user_role')
    if not role or role not in ('admin', 'super_admin'):
        return render_template('auth/unauthorized.html'), 403

    rest_response = None
    payload = None
    debug_error = None
    masked_config = {
        'supabase_url': Config.SUPABASE_URL,
        'service_key_len': len(Config.SUPABASE_SERVICE_KEY) if Config.SUPABASE_SERVICE_KEY else 0,
        'anon_key_len': len(Config.SUPABASE_KEY) if Config.SUPABASE_KEY else 0,
    }

    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name') or f"SafeDebug {datetime.now().isoformat()}"
            email = request.form.get('email') or f"safe+{int(datetime.now().timestamp())}@example.com"
            phone = request.form.get('phone') or None
            payload = {'full_name': full_name, 'email': email, 'phone': phone, 'created_at': datetime.now().isoformat()}

            rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
            rest_url = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
            if not rest_key or not rest_url:
                rest_response = {'error': 'missing SUPABASE_URL or key in config'}
            else:
                headers = {'apikey': rest_key.strip(), 'Authorization': f"Bearer {rest_key.strip()}", 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                r = requests.post(f"{rest_url}/rest/v1/students", headers=headers, json=payload, timeout=10)
                try:
                    headers_dict = dict(r.headers)
                except Exception:
                    headers_dict = {}
                # Try to parse JSON body if any
                body = None
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                rest_response = {'status_code': r.status_code, 'body': body, 'headers': headers_dict}
        except Exception:
            debug_error = traceback.format_exc()

    return render_template('admin/debug_supabase_safe.html', debug_error=debug_error, payload=payload, rest_response=rest_response, masked_config=masked_config)


# Production-safe debug status endpoint
# Usage: /admin/debug-status?token=<SECRET_KEY>
# Returns masked env info and simple counts for students/admissions/accepted
@admin_bp.route('/debug-status')
def debug_status():
    token = request.args.get('token') or request.headers.get('Authorization')
    if not token or token != Config.SECRET_KEY:
        return jsonify({'error': 'unauthorized'}), 403

    def mask(s):
        try:
            if not s:
                return None
            return f"{s[:6]}...{s[-6:]}"
        except Exception:
            return None

    info = {
        'supabase_url': mask(Config.SUPABASE_URL),
        'supabase_key_len': len(Config.SUPABASE_KEY) if Config.SUPABASE_KEY else 0,
        'supabase_service_key_len': len(Config.SUPABASE_SERVICE_KEY) if Config.SUPABASE_SERVICE_KEY else 0,
        'secret_key_len': len(Config.SECRET_KEY) if Config.SECRET_KEY else 0,
    }

    results = {}
    try:
        students = db.select('students') or []
        results['students_count_sample'] = len(students)
    except Exception as e:
        results['students_count_sample'] = f'error: {str(e)}'

    try:
        admissions = db.select('admissions') or []
        results['admissions_count_sample'] = len(admissions)
    except Exception as e:
        results['admissions_count_sample'] = f'error: {str(e)}'

    try:
        accepted = db.select('students', filters={'status': 'accepted'}) or []
        results['accepted_students_count_sample'] = len(accepted)
    except Exception as e:
        results['accepted_students_count_sample'] = f'error: {str(e)}'

    return jsonify({'info': info, 'results': results})


# Development-only, localhost-accessible debug route: direct REST insert without auth.
# This helps reproduce insert/permission problems from the development machine.
@admin_bp.route('/debug/local-supabase-test', methods=['POST'])
def debug_local_supabase_test():
    # Only allow when running in development and from localhost
    if Config.FLASK_ENV != 'development':
        return jsonify({'error': 'local debug only'}), 403
    if request.remote_addr not in ('127.0.0.1', '::1'):
        return jsonify({'error': 'local access only'}), 403

    try:
        full_name = request.form.get('full_name') or f"LocalDebug {datetime.now().isoformat()}"
        email = request.form.get('email') or f"local+{int(datetime.now().timestamp())}@example.com"
        phone = request.form.get('phone') or None
        payload = {'full_name': full_name, 'email': email, 'phone': phone, 'created_at': datetime.now().isoformat()}

        rest_key = (Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY) or None
        rest_url = Config.SUPABASE_URL.rstrip('/') if Config.SUPABASE_URL else None
        if not rest_key or not rest_url:
            return jsonify({'error': 'missing SUPABASE_URL or key in config'}), 500

        import requests
        headers = {'apikey': rest_key.strip(), 'Authorization': f"Bearer {rest_key.strip()}", 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        r = requests.post(f"{rest_url}/rest/v1/students", headers=headers, json=payload, timeout=15)

        try:
            body = r.json()
        except Exception:
            body = r.text

        return jsonify({'status_code': r.status_code, 'body': body, 'headers': dict(r.headers)})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@admin_bp.route('/enquiry/<int:enquiry_id>')
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def view_enquiry(enquiry_id):
    """View single enquiry with full student details"""
    enquiry = EnquiryModel.get_enquiry(enquiry_id)
    
    if not enquiry:
        flash('Enquiry not found', 'error')
        return redirect(url_for('admin.enquiries'))
    
    # Fetch full student details from students table
    student = None
    if enquiry.get('student_id'):
        students = db.select('students', filters={'id': enquiry['student_id']})
        student = students[0] if students else None
    
    # Fetch academic details from academics table
    academics = None
    if enquiry.get('student_id'):
        academic_records = db.select('academics', filters={'student_id': enquiry['student_id']})
        academics = academic_records[0] if academic_records else None
    
    return render_template('admin/view_enquiry.html', enquiry=enquiry, student=student, academics=academics)

@admin_bp.route('/enquiry/<int:enquiry_id>/update', methods=['POST'])
@check_module_access('enquiries')
@role_required(['super_admin', 'admin'])
def update_enquiry(enquiry_id):
    """Update enquiry status and response"""
    status = request.form.get('status')
    response = request.form.get('response')
    
    if not status:
        flash('Status is required', 'error')
        return redirect(url_for('admin.view_enquiry', enquiry_id=enquiry_id))
    
    try:
        EnquiryModel.update_enquiry_status(
            enquiry_id, 
            status, 
            response=response,
            assigned_to=session.get('user_id')
        )
        flash('Enquiry updated successfully', 'success')
        return redirect(url_for('admin.view_enquiry', enquiry_id=enquiry_id))
    except Exception as e:
        flash(f'Error updating enquiry: {str(e)}', 'error')
        return redirect(url_for('admin.view_enquiry', enquiry_id=enquiry_id))

@admin_bp.route('/report/daily')
@check_module_access('reports')
@role_required(['super_admin', 'admin'])
def daily_report():
    """Daily Admission Status Report"""
    report_date = request.args.get('date', str(date.today()))
    
    # Get all departments with seat information
    departments = DepartmentModel.get_all_departments()
    seats = SeatModel.get_all_seats(Config.ACADEMIC_YEAR)
    
    # Calculate admissions for each department
    report_data = []
    total_mq_seats = 0
    total_gq_seats = 0
    total_mq_admitted = 0
    total_gq_admitted = 0
    total_gq_special_admitted = 0
    
    for dept in departments:
        # Get seat info
        seat_info = next((s for s in seats if s['dept_id'] == dept['dept_id']), None)
        if not seat_info:
            continue
        
        mq_seats = seat_info['mq_seats']
        gq_seats = seat_info['gq_seats']
        
        # Count admissions
        apps = db.select('admission_applications', 
                        filters={'allocated_dept_id': dept['dept_id'],
                                'admission_status': 'allocated'})
        
        mq_admitted = len([a for a in apps if a['allocated_category'] == 'MQ'])
        gq_admitted = len([a for a in apps if a['allocated_category'] == 'GQ'])
        gq_special = len([a for a in apps if a['allocated_category'] == 'GQ(S)'])
        
        total_mq_seats += mq_seats
        total_gq_seats += gq_seats
        total_mq_admitted += mq_admitted
        total_gq_admitted += gq_admitted
        total_gq_special_admitted += gq_special
        
        report_data.append({
            'dept': dept,
            'mq_seats': mq_seats,
            'gq_seats': gq_seats,
            'mq_admitted': mq_admitted,
            'gq_admitted': gq_admitted,
            'gq_special': gq_special,
            'mq_vacancy': mq_seats - mq_admitted,
            'gq_vacancy': gq_seats - gq_admitted
        })
    
    return render_template('admin/daily_report.html',
                          report_data=report_data,
                          total_mq_seats=total_mq_seats,
                          total_gq_seats=total_gq_seats,
                          total_mq_admitted=total_mq_admitted,
                          total_gq_admitted=total_gq_admitted,
                          total_gq_special_admitted=total_gq_special_admitted,
                          report_date=report_date,
                          college_name=Config.COLLEGE_NAME,
                          academic_year=Config.ACADEMIC_YEAR)


@admin_bp.route('/test-email')
@check_module_access('reports')
@role_required(['super_admin', 'admin'])
def test_email():
    """Run quick EmailJS + SMTP validation and return JSON results."""
    results = {'emailjs': {}, 'smtp': {}}

    # EmailJS server-side calls removed to avoid 403 responses; skip EmailJS test
    results['emailjs'] = {'skipped': True, 'reason': 'EmailJS removed from server-side sends. Use SendGrid or client-side EmailJS.'}

    # SMTP test
    try:
        from utils.email_helper import send_email_smtp
        to_addr = Config.SMTP_USER or session.get('user_email') or 'pmcadmissions2026@gmail.com'
        subject = 'SMTP Test'
        body = 'This is a test email sent from the application to validate SMTP settings.'
        sent = send_email_smtp(subject, body, to_addr, from_name='App Test', reply_to=to_addr)
        results['smtp']['sent'] = bool(sent)
    except Exception as e:
        results['smtp']['exception'] = str(e)

    # Return JSON and flash summary
    summary = []
    if results['emailjs'].get('status_code') in (200, 202):
        summary.append('EmailJS OK')
    else:
        summary.append('EmailJS failed')
    if results['smtp'].get('sent'):
        summary.append('SMTP OK')
    else:
        summary.append('SMTP failed')

    flash(' / '.join(summary), 'info')
    return jsonify(results)

@admin_bp.route('/staff')
@check_module_access('staff')
@role_required(['super_admin', 'admin'])
def staff_management():
    """Manage staff and roles - view and edit staff members"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    
    # Get all users with admin/super_admin roles
    try:
        all_users = db.select('users')
        staff_list = []
        
        print(f"Total users fetched: {len(all_users) if all_users else 0}")  # Debug
        
        if all_users:
            for user_obj in all_users:
                print(f"User: {user_obj.get('first_name')} - Role ID: {user_obj.get('role_id')}")  # Debug
                # Show ALL users, not just admin roles
                role_names = {1: 'Super Admin', 2: 'Admin', 3: 'Faculty', 4: 'Staff'}
                role_name = role_names.get(user_obj.get('role_id'), 'Unknown')
                
                # Parse assigned_modules JSON (handle double-encoding)
                assigned_modules = user_obj.get('assigned_modules')
                if isinstance(assigned_modules, str):
                    try:
                        # First decode
                        decoded = json_lib.loads(assigned_modules)
                        # If result is still a string, decode again (double-encoded)
                        if isinstance(decoded, str):
                            decoded = json_lib.loads(decoded)
                        assigned_modules = decoded if isinstance(decoded, list) else []
                    except:
                        assigned_modules = []
                elif assigned_modules is None:
                    assigned_modules = []
                
                staff_list.append({
                    **user_obj,
                    'role_name': role_name,
                    'assigned_modules': assigned_modules,
                    'is_active': user_obj.get('is_active', True)
                })
        
        print(f"Staff list count: {len(staff_list)}")  # Debug
    except Exception as e:
        print(f"Error fetching staff: {str(e)}")
        staff_list = []
    
    return render_template('admin/staff_management.html',
                          user=user,
                          staff_members=staff_list)


@admin_bp.route('/staff/create', methods=['GET', 'POST'])
@check_module_access('staff')
@role_required(['super_admin', 'admin'])
def create_staff():
    """Create new staff member"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    
    if request.method == 'POST':
        try:
            employee_id = request.form.get('employee_id', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password', '').strip()
            role_id = request.form.get('role_id', '2')
            is_active = request.form.get('is_active') == 'on'
            
            # Validation
            if not all([employee_id, first_name, last_name, email, password]):
                flash('Employee ID, First Name, Last Name, Email, and Password are required', 'error')
                return redirect(url_for('admin.create_staff'))
            
            # Check if email already exists
            existing = db.select('users', filters={'email': email})
            if existing:
                flash('Email already exists', 'error')
                return redirect(url_for('admin.create_staff'))
            
            # Check if employee_id already exists
            existing_emp = db.select('users', filters={'employee_id': employee_id})
            if existing_emp:
                flash('Employee ID already exists', 'error')
                return redirect(url_for('admin.create_staff'))
            
            # Create new staff member
            staff_data = {
                'employee_id': employee_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone if phone else None,
                'password': password,  # Match schema field name
                'role_id': int(role_id),
                'is_active': is_active,
                'created_at': datetime.now().isoformat()
            }
            
            result = db.insert('users', staff_data)
            print(f"Insert result: {result}")  # Debug
            flash(f'Staff member {first_name} {last_name} created successfully (ID: {employee_id})', 'success')
            return redirect(url_for('admin.staff_management'))
            
        except Exception as e:
            print(f"Error creating staff: {str(e)}")  # Debug
            flash(f'Error creating staff: {str(e)}', 'error')
            return redirect(url_for('admin.create_staff'))
    
    return render_template('admin/create_staff.html', user=user)


@admin_bp.route('/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
@check_module_access('staff')
@role_required(['super_admin', 'admin'])
def edit_staff(staff_id):
    """Edit staff member"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    
    # Get staff member
    staff_data = db.select('users', filters={'user_id': staff_id})
    if not staff_data:
        flash('Staff member not found', 'error')
        return redirect(url_for('admin.staff_management'))
    
    staff = staff_data[0]
    
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            role_id = request.form.get('role_id', staff.get('role_id'))
            is_active = request.form.get('is_active') == 'on'
            
            # Get assigned modules from form
            assigned_modules = request.form.getlist('modules')
            
            # Validation
            if not all([first_name, last_name, email]):
                flash('First name, last name, and email are required', 'error')
                return redirect(url_for('admin.edit_staff', staff_id=staff_id))
            
            # Update staff member - store as clean JSON array
            update_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone if phone else None,
                'role_id': int(role_id),
                'is_active': is_active,
                'assigned_modules': json_lib.dumps(assigned_modules),  # Store clean JSON
                'updated_at': datetime.now().isoformat()
            }
            
            print(f"[DEBUG] update_staff: user_id={staff_id} payload={update_data}")
            try:
                res = db.update('users', update_data, {'user_id': staff_id})
                print(f"[DEBUG] db.update result: {res}")
            except Exception as e:
                import traceback
                print(f"[ERROR] db.update exception: {e}")
                traceback.print_exc()
                flash(f'Error updating staff: {str(e)}', 'error')
                return redirect(url_for('admin.edit_staff', staff_id=staff_id))

            flash(f'Staff member {first_name} {last_name} updated successfully', 'success')
            return redirect(url_for('admin.staff_management'))
            
        except Exception as e:
            flash(f'Error updating staff: {str(e)}', 'error')
            return redirect(url_for('admin.edit_staff', staff_id=staff_id))
    
    staff['role_name'] = 'Super Admin' if staff.get('role_id') == 1 else 'Admin'
    
    # Parse assigned_modules JSON if it exists
    assigned_modules = staff.get('assigned_modules')
    if isinstance(assigned_modules, str):
        try:
            staff['assigned_modules'] = json_lib.loads(assigned_modules)
        except:
            staff['assigned_modules'] = []
    elif assigned_modules is None:
        staff['assigned_modules'] = []
    
    # Get roles for dropdown
    roles = [
        {'role_id': 1, 'role_name': 'Super Admin'},
        {'role_id': 2, 'role_name': 'Admin'},
        {'role_id': 3, 'role_name': 'Faculty'},
        {'role_id': 4, 'role_name': 'Staff'}
    ]
    
    return render_template('admin/edit_staff.html', user=user, staff=staff, roles=roles)


@admin_bp.route('/staff/<int:staff_id>/delete', methods=['POST'])
@check_module_access('staff')
@role_required(['super_admin', 'admin'])
def delete_staff(staff_id):
    """Delete staff member"""
    try:
        staff_data = db.select('users', filters={'user_id': staff_id})
        if not staff_data:
            flash('Staff member not found', 'error')
        else:
            staff = staff_data[0]
            db.delete('users', {'user_id': staff_id})
            flash(f'Staff member {staff.get("first_name")} {staff.get("last_name")} deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting staff: {str(e)}', 'error')
    
    return redirect(url_for('admin.staff_management'))

@admin_bp.route('/staff/add', methods=['GET', 'POST'])
@role_required(['super_admin'])
def add_staff():
    """Add new staff member"""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        role_id = int(request.form.get('role_id'))
        
        # Validate inputs
        if not all([employee_id, email, password, first_name, role_id]):
            flash('Employee ID, Email, Password, First Name, and Role are required', 'error')
            return redirect(url_for('admin.add_staff'))
        
        # Check if user exists
        existing_user = db.select('users', filters={'email': email})
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('admin.add_staff'))
        
        # Check if employee ID exists
        existing_emp = db.select('users', filters={'employee_id': employee_id})
        if existing_emp:
            flash('Employee ID already exists', 'error')
            return redirect(url_for('admin.add_staff'))
        
        # Create user
        try:
            new_user = {
                'employee_id': employee_id,
                'email': email,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'role_id': role_id,
                'is_active': True
            }
            
            db.insert('users', new_user)
            
            # Log the action
            db.insert('audit_log', {
                'user_id': session.get('user_id'),
                'action': 'create_user',
                'timestamp': datetime.now().isoformat()
            })
            
            flash(f'Staff member {first_name} {last_name} added successfully!', 'success')
            return redirect(url_for('admin.staff_management'))
        except Exception as e:
            flash(f'Error adding staff: {str(e)}', 'error')
            return redirect(url_for('admin.add_staff'))
    
    # GET request - show form
    roles = db.select('roles')
    return render_template('admin/add_staff.html', roles=roles)

@admin_bp.route('/staff/<int:user_id>/toggle', methods=['POST'])
@check_module_access('staff')
@role_required(['super_admin'])
def toggle_staff_status(user_id):
    """Toggle staff active status"""
    user = db.select('users', filters={'user_id': user_id})
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    current_status = user[0]['is_active']
    new_status = not current_status
    
    db.update('users', {'is_active': new_status}, {'user_id': user_id})
    
    return jsonify({'success': True, 'new_status': new_status})

@admin_bp.route('/system-settings', methods=['POST'])
@role_required(['super_admin'])
def update_system_settings():
    """Update system-wide settings"""
    from flask import request, jsonify
    
    try:
        setting_name = request.json.get('setting')
        setting_value = request.json.get('value')
        
        # Here you can save settings to database or cache
        # For now, just log it
        print(f"System Setting Updated: {setting_name} = {setting_value}")
        
        return jsonify({'success': True, 'message': f'{setting_name} updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/profile')
@role_required(['super_admin', 'admin'])
def profile():
    """User profile page"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    return render_template('admin/settings.html', user=user)


# Departments management
@admin_bp.route('/departments')
@role_required(['super_admin'])
def departments():
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Super Admin'

    depts = db.select('departments') or []

    # Compute admitted counts per department (cumulative upto today) similar to reports
    try:
        # initialize counters on dept dicts
        dept_map = {}
        for d in depts:
            d['adm_gq_upto'] = int(d.get('adm_gq_upto') or 0)
            d['adm_mq_upto'] = int(d.get('adm_mq_upto') or 0)
            d['admitted_gq'] = int(d.get('admitted_gq') or d.get('adm_gq_upto') or 0)
            d['admitted_mq'] = int(d.get('admitted_mq') or d.get('adm_mq_upto') or 0)
            dept_map[int(d.get('id'))] = d

        today = datetime.utcnow().date()
        all_counselling = db.select('counselling_records') or []
        for rec in all_counselling:
            created = rec.get('created_at')
            if not created:
                continue
            try:
                if isinstance(created, str):
                    created_dt = datetime.fromisoformat(created.replace(' ', 'T'))
                else:
                    created_dt = created
                created_date = created_dt.date()
            except Exception:
                continue

            if created_date > today:
                # ignore future records
                continue

            dept_id = int(rec.get('allotted_dept_id') or 0)
            dept = dept_map.get(dept_id)
            if not dept:
                continue
            quota = (rec.get('quota_type') or '').upper()
            if quota == 'GQ':
                dept['adm_gq_upto'] = int(dept.get('adm_gq_upto', 0)) + 1
            elif quota == 'MQ':
                dept['adm_mq_upto'] = int(dept.get('adm_mq_upto', 0)) + 1
            else:
                # if other quota categories exist, count them as GQ slot fallback in template logic
                dept['adm_gq_upto'] = int(dept.get('adm_gq_upto', 0)) + 1

        # mirror counts into compatibility keys used by templates
        for d in depts:
            d['admitted_gq'] = int(d.get('admitted_gq') or d.get('adm_gq_upto') or 0)
            d['admitted_mq'] = int(d.get('admitted_mq') or d.get('adm_mq_upto') or 0)
    except Exception as e:
        print(f"Error computing department admitted counts: {e}")

    return render_template('admin/departments.html', user=user, departments=depts)


@admin_bp.route('/departments/new', methods=['POST'])
@role_required(['super_admin'])
def create_department():
    try:
        dept_code = request.form.get('dept_code')
        dept_name = request.form.get('dept_name')
        short_name = request.form.get('short_name')
        description = request.form.get('description')
        # Backwards-compatible: accept either seats or new gq/mq fields
        seats = int(request.form.get('seats') or 0)
        gq_seats = int(request.form.get('gq_seats') or request.form.get('gq') or 0)
        mq_seats = int(request.form.get('mq_seats') or request.form.get('mq') or 0)

        data = {
            'dept_code': dept_code,
            'dept_name': dept_name,
            'short_name': short_name,
            'description': description,
            'seats': seats,
            'gq_seats': gq_seats,
            'mq_seats': mq_seats,
            'is_active': True
        }
        db.insert('departments', data)
        flash('Department created', 'success')
    except Exception as e:
        print(f"Create department error: {e}")
        flash('Error creating department', 'error')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@role_required(['super_admin'])
def edit_department(dept_id):
    if request.method == 'GET':
        d = db.select('departments', filters={'id': dept_id})
        if not d:
            flash('Department not found', 'error')
            return redirect(url_for('admin.departments'))
        return render_template('admin/department_edit.html', dept=d[0])

    # POST update
    try:
        dept_code = request.form.get('dept_code')
        dept_name = request.form.get('dept_name')
        short_name = request.form.get('short_name')
        description = request.form.get('description')
        # Backwards-compatible: accept new gq/mq seat fields
        seats = int(request.form.get('seats') or 0)
        gq_seats = int(request.form.get('gq_seats') or request.form.get('gq') or 0)
        mq_seats = int(request.form.get('mq_seats') or request.form.get('mq') or 0)
        is_active = True if request.form.get('is_active') in ('1','true','on') else False

        update_payload = {
            'dept_code': dept_code,
            'dept_name': dept_name,
            'short_name': short_name,
            'description': description,
            'seats': seats,
            'gq_seats': gq_seats,
            'mq_seats': mq_seats,
            'is_active': is_active
        }

        db.update('departments', update_payload, {'id': dept_id})
        flash('Department updated', 'success')
    except Exception as e:
        print(f"Edit department error: {e}")
        flash('Error updating department', 'error')

    return redirect(url_for('admin.departments'))


@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@role_required(['super_admin'])
def delete_department(dept_id):
    try:
        db.delete('departments', {'id': dept_id})
        flash('Department deleted', 'success')
    except Exception as e:
        print(f"Delete department error: {e}")
        flash('Error deleting department', 'error')
    return redirect(url_for('admin.departments'))

@admin_bp.route('/reports')
@role_required(['super_admin', 'admin'])
def reports():
    """Admission reports page"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'User'
    
    # Get basic stats for reports
    total_enquiries = db.count('enquiries')
    total_applications = db.count('admission_applications')
    total_students = db.count('students')

    # Load departments (for seat counts and admitted counts)
    departments = db.select('departments') or []

    # Date selector - allow user to pick a date to aggregate admissions up to that day
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            selected_date = datetime.utcnow().date()
    else:
        selected_date = datetime.utcnow().date()

    # Prepare department lookup and initialize counters (both upto and on-date)
    dept_map = {}
    for d in departments:
        # ensure numeric seats fields exist - prefer new gq_seats/mq_seats fields
        d['mq'] = int(d.get('mq_seats') or d.get('mq') or 0)
        d['gq'] = int(d.get('gq_seats') or d.get('gq') or d.get('seats') or 0)
        # admission counters: cumulative (upto) and on-date
        d['adm_mq_upto'] = 0
        d['adm_gq_upto'] = 0
        d['adm_gqs_upto'] = 0
        d['adm_mq_on'] = 0
        d['adm_gq_on'] = 0
        d['adm_gqs_on'] = 0
        dept_map[int(d.get('id'))] = d

    # Aggregate counselling records: compute cumulative (upto) and on-date counts
    try:
        all_counselling = db.select('counselling_records') or []
        for rec in all_counselling:
            created = rec.get('created_at')
            if not created:
                continue
            # created may be a string; try to parse to datetime
            try:
                if isinstance(created, str):
                    created_dt = datetime.fromisoformat(created.replace(' ', 'T'))
                else:
                    created_dt = created
                created_date = created_dt.date()
            except Exception:
                continue

            dept_id = int(rec.get('allotted_dept_id') or 0)
            dept = dept_map.get(dept_id)
            if not dept:
                continue
            quota = (rec.get('quota_type') or '').upper()

            # cumulative upto (inclusive)
            if created_date <= selected_date:
                if quota == 'GQ':
                    dept['adm_gq_upto'] = int(dept.get('adm_gq_upto', 0)) + 1
                elif quota == 'MQ':
                    dept['adm_mq_upto'] = int(dept.get('adm_mq_upto', 0)) + 1
                else:
                    dept['adm_gqs_upto'] = int(dept.get('adm_gqs_upto', 0)) + 1

            # on-date (exact match)
            if created_date == selected_date:
                if quota == 'GQ':
                    dept['adm_gq_on'] = int(dept.get('adm_gq_on', 0)) + 1
                elif quota == 'MQ':
                    dept['adm_mq_on'] = int(dept.get('adm_mq_on', 0)) + 1
                else:
                    dept['adm_gqs_on'] = int(dept.get('adm_gqs_on', 0)) + 1
    except Exception as e:
        print(f"Error aggregating counselling records: {e}")

    selected_date_iso = selected_date.isoformat()
    selected_date_display = selected_date.strftime('%d.%m.%Y')

    # Compute totals
    total_mq_seats = sum([int(d.get('mq') or 0) for d in departments])
    total_gq_seats = sum([int(d.get('gq') or 0) for d in departments])
    # totals: cumulative (upto)
    total_mq_adm_upto = sum([int(d.get('adm_mq_upto') or 0) for d in departments])
    total_gq_adm_upto = sum([int(d.get('adm_gq_upto') or 0) for d in departments])
    total_gqs_adm_upto = sum([int(d.get('adm_gqs_upto') or 0) for d in departments])
    # totals: on-date
    total_mq_adm_on = sum([int(d.get('adm_mq_on') or 0) for d in departments])
    total_gq_adm_on = sum([int(d.get('adm_gq_on') or 0) for d in departments])
    total_gqs_adm_on = sum([int(d.get('adm_gqs_on') or 0) for d in departments])

    return render_template('admin/reports.html',
                          user=user,
                          total_enquiries=total_enquiries,
                          total_applications=total_applications,
                          total_students=total_students,
                          departments=departments,
                          selected_date_iso=selected_date_iso,
                          selected_date_display=selected_date_display,
                          totalMqSeats=total_mq_seats,
                          totalGqSeats=total_gq_seats,
                          totalMqAdmUpto=total_mq_adm_upto,
                          totalGqAdmUpto=total_gq_adm_upto,
                          totalGqsAdmUpto=total_gqs_adm_upto,
                          totalMqAdmOn=total_mq_adm_on,
                          totalGqAdmOn=total_gq_adm_on,
                          totalGqsAdmOn=total_gqs_adm_on)


@admin_bp.route('/reports/update-admissions', methods=['POST'])
@role_required(['super_admin', 'admin'])
def reports_update_admissions():
    """Update admitted counts per department (from reports UI)"""
    try:
        # Expect payload like {'dept_<id>': '12', ...}
        data = request.form or request.json or {}
        updated = 0
        for key, val in data.items():
            if key.startswith('dept_'):
                try:
                    dept_id = int(key.split('_', 1)[1])
                    admitted = int(val) if val not in (None, '') else 0
                    db.update('departments', {'admitted_count': admitted}, {'id': dept_id})
                    updated += 1
                except Exception:
                    continue
        flash(f'Updated admitted counts for {updated} departments', 'success')
    except Exception as e:
        print(f"Error updating admitted counts: {e}")
        flash('Error updating admitted counts', 'error')

    return redirect(url_for('admin.reports'))

# Multi-Step Admission Process Routes

@admin_bp.route('/enquiries/step1/<int:enquiry_id>', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
def enquiry_step1(enquiry_id):
    """Step 1: Student Enquiry Form - Personal & Academic Details"""
    # Get enquiry details
    enquiry = db.select('enquiries', filters={'enquiry_id': enquiry_id})
    if not enquiry:
        flash('Enquiry not found', 'error')
        return redirect(url_for('admin.enquiries'))
    
    enquiry = enquiry[0]
    
    if request.method == 'POST':
        try:
            # Extract form data
            full_name = request.form.get('full_name')
            whatsapp_number = request.form.get('whatsapp_number')
            email = request.form.get('email')
            father_name = request.form.get('father_name')
            mother_name = request.form.get('mother_name')
            school_name = request.form.get('school_name')
            board = request.form.get('board')
            maths_marks = request.form.get('maths_marks')
            physics_marks = request.form.get('physics_marks')
            chemistry_marks = request.form.get('chemistry_marks')
            religion = request.form.get('religion')
            community = request.form.get('community')
            quota_type = request.form.get('quota_type')
            
            # Create/Update student with enquiry data
            student_data = {
                'full_name': full_name,
                'email': email,
                'whatsapp_number': whatsapp_number,
                'father_name': father_name,
                'mother_name': mother_name,
                'community': community,
                'religion': religion
            }
            
            # Check if student already exists for this enquiry
            existing_student = db.select('students', filters={'enquiry_id': enquiry_id})
            
            if existing_student:
                db.update('students', student_data, {'enquiry_id': enquiry_id})
                student_id = existing_student[0]['student_id']
            else:
                result = db.insert('students', {**student_data, 'enquiry_id': enquiry_id})
                student_id = result
            
            # Create/Update academic record
            academic_data = {
                'student_id': student_id,
                'school_name': school_name,
                'board': board,
                'maths_marks': float(maths_marks) if maths_marks else 0,
                'physics_marks': float(physics_marks) if physics_marks else 0,
                'chemistry_marks': float(chemistry_marks) if chemistry_marks else 0,
                'cutoff_score': calculate_cutoff(maths_marks, physics_marks, chemistry_marks),
                'quota_type': quota_type
            }
            
            existing_academic = db.select('academics', filters={'student_id': student_id})
            if existing_academic:
                db.update('academics', academic_data, {'student_id': student_id})
            else:
                db.insert('academics', academic_data)
            
            # Log the action
            db.insert('audit_log', {
                'user_id': session.get('user_id'),
                'action': 'enquiry_step1_completed',
                'timestamp': datetime.now().isoformat()
            })
            
            flash('Enquiry details saved successfully!', 'success')
            return redirect(url_for('admin.enquiry_step2', enquiry_id=enquiry_id))
        
        except Exception as e:
            flash(f'Error saving enquiry details: {str(e)}', 'error')
    
    return render_template('admin/enquiry_step1.html', enquiry=enquiry)


@admin_bp.route('/assign-branch/<int:student_id>', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
@check_module_access('branch_selection')
def assign_branch(student_id):
    """Assign department/branch to a student"""
    # Get student details
    student = db.select('students', filters={'id': student_id})
    
    if not student or len(student) == 0:
        flash('Student not found', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    
    student = student[0]
    
    # Get academic details for cutoff
    academic = db.select('academics', filters={'student_id': student_id})
    academic = academic[0] if academic else None
    
    # Get all active departments
    try:
        departments_response = db.client.table('departments').select('*').eq('is_active', True).execute()
        departments = departments_response.data if departments_response.data else []
        print(f"DEBUG: Departments fetched successfully: {len(departments)} departments")
        if departments:
            print(f"DEBUG: First department structure: {departments[0]}")
    except Exception as e:
        print(f"DEBUG: Error fetching departments via Supabase client: {e}")
        try:
            departments = db.select('departments', filters={'is_active': True})
            print(f"DEBUG: Departments fetched via db.select: {len(departments)} departments")
        except Exception as e2:
            print(f"DEBUG: Error with db.select: {e2}")
            departments = []
    
    if request.method == 'POST':
        # Block POST if student not yet accepted by admin
        if student.get('status') != 'accepted':
            flash('Student must be accepted by an admin before assigning branches.', 'error')
            return redirect(url_for('admin.assign_branch', student_id=student_id))

        try:
            preferred_dept_id = request.form.get('preferred_dept_id')
            optional_dept_ids = request.form.getlist('optional_dept_ids')  # Get multiple values
            application_number = request.form.get('application_number')  # Get manual application number
            
            if not preferred_dept_id:
                flash('Please select a preferred department', 'error')
                return redirect(url_for('admin.assign_branch', student_id=student_id))
            
            # Convert optional_dept_ids list to JSON array for storage
            optional_depts_json = optional_dept_ids if optional_dept_ids else None  # Store as list (will be converted to JSON)
            
            # Check if admission record already exists
            existing_admission = db.select('admissions', filters={'student_id': student_id})
            
            admission_data = {
                'student_id': student_id,
                'preferred_dept_id': int(preferred_dept_id),
                'optional_dept_ids': optional_depts_json,  # Store as JSON array
                'status': 'branch_selection_pending',
                'updated_at': datetime.now().isoformat()
            }

            # Attach processed_by and processed_at (who performed the assignment)
            current_user = get_current_user()
            if current_user:
                processed_by = f"{current_user.get('first_name','').strip()} {current_user.get('last_name','').strip()}".strip()
                if processed_by:
                    admission_data['processed_by'] = processed_by
                    admission_data['processed_at'] = datetime.now().isoformat()
            
            # If application number provided, update admission_applications table
            if application_number:
                try:
                    # Check if admission_applications record exists
                    existing_app = db.select('admission_applications', filters={'student_id': student_id})
                    app_data = {
                        'student_id': student_id,
                        'application_number': application_number,
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if existing_app and len(existing_app) > 0:
                        db.update('admission_applications', app_data, {'student_id': student_id})
                    else:
                        app_data['created_at'] = datetime.now().isoformat()
                        db.insert('admission_applications', app_data)
                    print(f"DEBUG: Application number {application_number} saved for student {student_id}")
                except Exception as app_err:
                    print(f"DEBUG: Error saving application number: {app_err}")
            
            if existing_admission and len(existing_admission) > 0:
                # Update existing record
                try:
                    db.update('admissions', admission_data, {'student_id': student_id})
                    print(f"Updated admission record for student {student_id}")
                    flash(f'Branch selection updated for {student.get("full_name")}!', 'success')
                except Exception as update_err:
                    print(f"Update error: {update_err}")
                    flash(f'Error updating branch selection: {str(update_err)}', 'error')
                    return redirect(url_for('admin.assign_branch', student_id=student_id))
            else:
                # Create new record
                try:
                    admission_data['created_at'] = datetime.now().isoformat()
                    result = db.insert('admissions', admission_data)
                    print(f"Inserted new admission record: {result}")
                    if result:
                        flash(f'Branch assigned successfully to {student.get("full_name")}!', 'success')
                    else:
                        flash('Error: Branch selection was not saved. Please try again.', 'error')
                        return redirect(url_for('admin.assign_branch', student_id=student_id))
                except Exception as insert_err:
                    print(f"Insert error: {insert_err}")
                    flash(f'Error saving branch selection: {str(insert_err)}', 'error')
                    return redirect(url_for('admin.assign_branch', student_id=student_id))
            
            return redirect(url_for('admin.admin_dashboard'))
        
        except Exception as e:
            flash(f'Error assigning branch: {str(e)}', 'error')
            print(f"Branch assignment error: {e}")
            return redirect(url_for('admin.assign_branch', student_id=student_id))
    
    return render_template('admin/branch_selection.html',
                          student=student,
                          academic=academic,
                          departments=departments)


@admin_bp.route('/accept-student/<int:student_id>', methods=['POST'])
@check_module_access('branch_selection')
@role_required(['admin', 'super_admin'])
def accept_student(student_id):
    """Accept a student: mark status, generate unique_id if missing, and record who accepted."""
    user = get_current_user()
    if not user:
        flash('Unauthorized action', 'error')
        return redirect(url_for('admin.enquiries'))

    student_data = db.select('students', filters={'id': student_id})
    if not student_data:
        flash('Student not found', 'error')
        return redirect(url_for('admin.enquiries'))

    student = student_data[0]
    if student.get('status') == 'accepted':
        flash('Student already accepted', 'info')
        return redirect(url_for('admin.assign_branch', student_id=student_id))

    # Generate unique_id if not present
    unique_id = student.get('unique_id')
    if not unique_id:
        unique_id = f"STU-{datetime.now().year}-{student_id}"

    accepted_by = f"{user.get('first_name','').strip()} {user.get('last_name','').strip()}".strip()
    update_data = {
        'status': 'accepted',
        'accepted_by': accepted_by,
        'accepted_at': datetime.now().isoformat(),
        'unique_id': unique_id
    }

    try:
        db.update('students', update_data, {'id': student_id})
        flash('Student accepted successfully. You can now assign branches.', 'success')
    except Exception as e:
        print(f"Error marking student accepted: {e}")
        traceback.print_exc()
        flash('Error accepting student', 'error')

    return redirect(url_for('admin.assign_branch', student_id=student_id))


@admin_bp.route('/enquiries/step2/<int:enquiry_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def enquiry_step2(enquiry_id):
    """Step 2: Branch Selection - Department Allocation"""
    enquiry = db.select('enquiries', filters={'enquiry_id': enquiry_id})
    if not enquiry:
        flash('Enquiry not found', 'error')
        return redirect(url_for('admin.enquiries'))
    
    enquiry = enquiry[0]
    
    # Get student and departments
    student = db.select('students', filters={'enquiry_id': enquiry_id})
    student = student[0] if student else None
    
    departments = db.select('departments')
    
    if request.method == 'POST':
        try:
            primary_dept = request.form.get('primary_department')
            secondary_dept = request.form.get('secondary_department')
            
            # Create admission application
            app_data = {
                'student_id': student['student_id'],
                'enquiry_id': enquiry_id,
                'primary_department': primary_dept,
                'secondary_department': secondary_dept,
                'status': 'branch_selected',
                'created_at': datetime.now().isoformat()
            }
            
            existing_app = db.select('admission_applications', filters={'enquiry_id': enquiry_id})
            
            if existing_app:
                db.update('admission_applications', app_data, {'enquiry_id': enquiry_id})
            else:
                db.insert('admission_applications', app_data)
            
            # Log the action
            db.insert('audit_log', {
                'user_id': session.get('user_id'),
                'action': 'enquiry_step2_completed',
                'timestamp': datetime.now().isoformat()
            })
            
            flash('Branch selection saved successfully!', 'success')
            return redirect(url_for('admin.enquiry_step3', enquiry_id=enquiry_id))
        
        except Exception as e:
            flash(f'Error saving branch selection: {str(e)}', 'error')
    
    return render_template('admin/enquiry_step2.html', 
                          enquiry=enquiry, 
                          student=student,
                          departments=departments)


@admin_bp.route('/enquiries/step3/<int:enquiry_id>', methods=['GET', 'POST'])
@role_required(['super_admin', 'admin'])
def enquiry_step3(enquiry_id):
    """Step 3: Final Review & Application Filing Summary"""
    enquiry = db.select('enquiries', filters={'enquiry_id': enquiry_id})
    if not enquiry:
        flash('Enquiry not found', 'error')
        return redirect(url_for('admin.enquiries'))
    
    enquiry = enquiry[0]
    
    # Get all related data
    student = db.select('students', filters={'enquiry_id': enquiry_id})
    student = student[0] if student else None
    
    academic = db.select('academics', filters={'student_id': student['student_id']}) if student else []
    academic = academic[0] if academic else None
    
    application = db.select('admission_applications', filters={'enquiry_id': enquiry_id})
    application = application[0] if application else None
    
    if request.method == 'POST':
        try:
            # Mark application as submitted
            if application:
                db.update('admission_applications', 
                         {'status': 'submitted', 'submitted_at': datetime.now().isoformat()},
                         {'admission_id': application['admission_id']})
            
            # Update enquiry status
            db.update('enquiries', 
                     {'status': 'converted', 'converted_at': datetime.now().isoformat()},
                     {'enquiry_id': enquiry_id})
            
            # Log the action
            db.insert('audit_log', {
                'user_id': session.get('user_id'),
                'action': 'enquiry_step3_completed',
                'timestamp': datetime.now().isoformat()
            })
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('admin.applications'))
        
        except Exception as e:
            flash(f'Error submitting application: {str(e)}', 'error')
    
    return render_template('admin/enquiry_step3.html', 
                          enquiry=enquiry,
                          student=student,
                          academic=academic,
                          application=application)


@admin_bp.route('/applications', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
def applications():
    """Step 3: Document Upload for Applications"""
    user = get_current_user()
    
    # Get student_id from request (either GET or POST)
    student_id = request.args.get('student_id') or request.form.get('student_id')
    
    if not student_id:
        # Show list of students to choose from
        try:
            # Try to get all students who have been assigned branches
            assigned_students = db.select('admissions')
            print(f"DEBUG: Found {len(assigned_students) if assigned_students else 0} assigned students")
            
            pending_students = []
            completed_students = []
            
            if assigned_students:
                for admission in assigned_students:
                    try:
                        student_data = db.select('students', filters={'id': admission['student_id']})
                        if student_data and len(student_data) > 0:
                            student = student_data[0]
                            
                            # Check if documents have been uploaded
                            app_data = db.select('admission_applications', filters={'student_id': admission['student_id']})
                            documents_count = 0
                            app_id = None
                            application_number = None
                            if app_data and len(app_data) > 0:
                                documents_count = app_data[0].get('documents_count', 0)
                                app_id = app_data[0].get('app_id')
                                application_number = app_data[0].get('registration_id') or app_data[0].get('application_number') or f"APP-{app_id}"
                            
                            student_info = {
                                'id': student['id'],
                                'name': student.get('full_name', 'Unknown'),
                                'unique_id': student.get('unique_id', 'N/A'),
                                'documents_count': documents_count,
                                'app_id': app_id,
                                'application_number': application_number
                            }
                            
                            # Separate into pending and completed
                            if documents_count > 0:
                                completed_students.append(student_info)
                            else:
                                pending_students.append(student_info)
                    except Exception as e:
                        print(f"Error fetching student {admission['student_id']}: {e}")
                        continue
            
            print(f"DEBUG: Prepared {len(pending_students)} pending and {len(completed_students)} completed students for display")
            return render_template('admin/select_student.html', 
                                 pending_students=pending_students,
                                 completed_students=completed_students)
        except Exception as e:
            print(f"ERROR loading students: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error loading students: {str(e)}', 'error')
            return redirect(url_for('admin.admin_dashboard'))
    
    try:
        student_id = int(student_id)
    except:
        flash('Invalid Student ID', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    
    # Get student details
    student_data = db.select('students', filters={'id': student_id})
    if not student_data or len(student_data) == 0:
        flash('Student not found', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    
    student = student_data[0]
    
    if request.method == 'POST':
        try:
            print(f"\n{'='*60}")
            print(f"DEBUG: Processing document upload for student_id: {student_id}")
            
            # Get application number from form
            application_number = request.form.get('application_number')
            if application_number:
                print(f"DEBUG: Application number provided: {application_number}")
                # Save to admission_applications table
                try:
                    existing_app = db.select('admission_applications', filters={'student_id': student_id})
                    app_data = {
                        'student_id': student_id,
                        'registration_id': application_number,
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if existing_app and len(existing_app) > 0:
                        db.update('admission_applications', app_data, {'student_id': student_id})
                        print(f"DEBUG: Updated application number for student {student_id}")
                    else:
                        app_data['created_at'] = datetime.now().isoformat()
                        db.insert('admission_applications', app_data)
                        print(f"DEBUG: Inserted new application number for student {student_id}")
                except Exception as app_err:
                    print(f"DEBUG: Error saving application number: {app_err}")
            print(f"DEBUG: Form files received: {request.files.keys()}")
            print(f"{'='*60}")
            
            # Get all uploaded files
            files_to_upload = {
                'file_10th_mark': '10th_Mark_Sheet',
                'file_12th_mark': '12th_Mark_Sheet',
                'file_community': 'Community_Certificate',
                'file_fg': 'FG_Certificate',
                'file_photo': 'Passport_Photo',
                'file_tc': 'Transfer_Certificate'
            }
            
            uploaded_files = {}
            failed_files = []
            max_file_size = 5 * 1024 * 1024  # 5MB
            
            # Check if at least one file is uploaded (not required to upload all)
            has_any_file = any(request.files.get(key) and request.files.get(key).filename != '' for key in files_to_upload.keys())
            
            if not has_any_file:
                print("DEBUG: No files uploaded")
                flash('Please upload at least one document', 'error')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Please upload at least one document'}), 400
                return redirect(url_for('admin.applications', student_id=student_id))
            
            for file_key, file_label in files_to_upload.items():
                file = request.files.get(file_key)
                print(f"DEBUG: Checking {file_key}... File object: {file}")
                
                if file and file.filename != '':
                    print(f"  ✓ File found: {file.filename}")
                    
                    # Validate file size
                    file.seek(0, 2)  # Seek to end
                    file_size = file.tell()
                    file.seek(0)  # Seek back to start
                    print(f"  File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
                    
                    if file_size > max_file_size:
                        print(f"  ✗ File exceeds 5MB limit")
                        failed_files.append(f'{file_label} exceeds 5MB limit')
                        continue
                    
                    # Validate file type
                    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
                    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    print(f"  File extension: {file_ext}")
                    
                    if not file_ext or file_ext not in allowed_extensions:
                        print(f"  ✗ Invalid file format")
                        failed_files.append(f'{file_label} has invalid format. Use PDF or JPEG/PNG')
                        continue
                    
                    # Upload to Supabase bucket
                    try:
                        bucket_name = 'Student_files'
                        file_path = f"student_{student_id}/{file_label}_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.{file_ext}"
                        print(f"  Uploading to: {file_path}")
                        
                        file_content = file.read()
                        print(f"  Content read: {len(file_content)} bytes")
                        
                        try:
                            response = db.client.storage.from_(bucket_name).upload(
                                file_path,
                                file_content,
                                {"contentType": file.content_type}
                            )
                            print(f"  ✓ Upload response type: {type(response)}, value: {response}")
                        except Exception as resp_err:
                            print(f"  ✗ Upload returned error: {resp_err}")
                            raise
                        
                        # Get public URL
                        try:
                            public_url_response = db.client.storage.from_(bucket_name).get_public_url(file_path)
                            print(f"  Public URL response type: {type(public_url_response)}, value: {public_url_response}")
                            
                            if isinstance(public_url_response, dict) and 'publicUrl' in public_url_response:
                                url = public_url_response['publicUrl']
                            elif isinstance(public_url_response, str):
                                url = public_url_response
                            else:
                                url = str(public_url_response)
                            
                            # Add download parameter for PDFs to avoid browser preview issues
                            if file_ext.lower() == 'pdf':
                                url = f"{url}?download"
                            
                            print(f"  ✓ Public URL: {url}")
                            
                            uploaded_files[file_label] = {
                                'path': file_path,
                                'url': url,
                                'size': file_size,
                                'uploaded_at': datetime.now().isoformat()
                            }
                            print(f"  ✓ {file_label} stored in uploaded_files dict")
                            
                        except Exception as url_err:
                            print(f"  ✗ URL generation error: {url_err}")
                            # Still save even if URL fails
                            uploaded_files[file_label] = {
                                'path': file_path,
                                'url': None,
                                'size': file_size,
                                'uploaded_at': datetime.now().isoformat()
                            }
                            print(f"  ⚠ {file_label} stored without URL")
                        
                    except Exception as upload_err:
                        print(f"  ✗ Upload error: {upload_err}")
                        import traceback
                        traceback.print_exc()
                        failed_files.append(f'{file_label}: {str(upload_err)}')
                        continue
                else:
                    print(f"  - File not provided (optional or not submitted)")
            
            # Check if at least one file was uploaded
            if not uploaded_files:
                flash('Please upload at least one document', 'error')
                return redirect(url_for('admin.applications', student_id=student_id))
            
            # Get current user for uploaded_by field
            current_user = get_current_user()
            uploaded_by = current_user.get('id') if current_user else None
            
            # Get admission application record to get app_id
            try:
                admission_app = db.select('admission_applications', filters={'student_id': student_id})
                
                if not admission_app or len(admission_app) == 0:
                    # Create a new admission application record if doesn't exist
                    app_data = {
                        'student_id': student_id,
                        'created_at': datetime.now().isoformat()
                    }
                    print(f"DEBUG: Creating admission_applications record with data: {app_data}")
                    app_result = db.insert('admission_applications', app_data)
                    if app_result:
                        print(f"DEBUG: ✓ admission_applications record created")
                        admission_app = db.select('admission_applications', filters={'student_id': student_id})
                    else:
                        print(f"DEBUG: ✗ Failed to create admission_applications record")
                        flash('Error creating application record', 'error')
                        return redirect(url_for('admin.applications', student_id=student_id))
                
                app_id = admission_app[0].get('app_id') if admission_app and len(admission_app) > 0 else None
                print(f"DEBUG: admission_app_id = {app_id}")
                
                if not app_id:
                    flash('Error: Could not find application ID', 'error')
                    return redirect(url_for('admin.applications', student_id=student_id))
                
                # Insert each document into documents table
                documents_inserted = 0
                document_insertion_errors = []
                
                for doc_type, doc_info in uploaded_files.items():
                    try:
                        doc_record = {
                            'app_id': app_id,
                            'document_type': doc_type,
                            'document_url': doc_info.get('url'),
                            'file_size': doc_info.get('size'),
                            'uploaded_by': uploaded_by,
                            'created_at': datetime.now().isoformat()
                        }
                        print(f"DEBUG: Inserting {doc_type} with data: {doc_record}")
                        
                        result = db.insert('documents', doc_record)
                        if result:
                            documents_inserted += 1
                            print(f"✓ Inserted {doc_type} into documents table (row ID: {result})")
                        else:
                            document_insertion_errors.append(f'{doc_type}: Database error')
                            print(f"✗ Failed to insert {doc_type} into documents table")
                    
                    except Exception as db_err:
                        print(f"✗ Database insertion error for {doc_type}: {db_err}")
                        import traceback
                        traceback.print_exc()
                        document_insertion_errors.append(f'{doc_type}: {str(db_err)}')
                        continue
                
                # Update admission_applications table with document count
                # Note: Trigger will auto-update documents_count via database
                try:
                    print(f"DEBUG: Updating admission_applications for app_id: {app_id} with {documents_inserted} documents")
                    update_app_data = {
                        'updated_at': datetime.now().isoformat()
                    }
                    db.update('admission_applications', update_app_data, {'app_id': app_id})
                    print(f"✓ Updated admission_applications for app_id: {app_id}")
                    print(f"  Note: Trigger will auto-update step3_completed and documents_count")
                except Exception as app_update_err:
                    print(f"✗ Error updating admission_applications: {app_update_err}")
                
                # Build success message
                if documents_inserted > 0:
                    success_msg = f'✓ {documents_inserted} document(s) uploaded successfully for {student.get("full_name")}!'
                    if failed_files:
                        success_msg += f'\n⚠ {len(failed_files)} file(s) failed to upload'
                    if document_insertion_errors:
                        success_msg += f'\n⚠ {len(document_insertion_errors)} file(s) failed to save to database'
                    flash(success_msg, 'success')
                    
                    # Check if this is an AJAX request (from modal)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': True, 'message': success_msg, 'documents_inserted': documents_inserted})
                    return redirect(url_for('admin.admin_dashboard'))
                else:
                    flash('Error saving documents to database. Please try again.', 'error')
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'error': 'Error saving documents to database'}), 400
                    return redirect(url_for('admin.applications', student_id=student_id))
                    
            except Exception as app_err:
                print(f"Application processing error: {app_err}")
                flash(f'Error processing documents: {str(app_err)}', 'error')
        
        except Exception as e:
            print(f"Document upload error: {e}")
            flash(f'Error during upload: {str(e)}', 'error')
    
    return render_template('admin/document_upload.html',
                          student=student,
                          application_id=f"ADM-{datetime.now().year}-{student_id}")


def calculate_cutoff(maths, physics, chemistry):
    """Calculate cutoff score: (Maths + (Physics + Chemistry)/2)"""
    try:
        maths = float(maths) if maths else 0
        physics = float(physics) if physics else 0
        chemistry = float(chemistry) if chemistry else 0
        return maths + ((physics + chemistry) / 2)
    except:
        return 0


@admin_bp.route('/admin/documents-management')
@role_required(['admin', 'super_admin'])
def documents_management():
    """Manage student documents - view and edit document uploads"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'
    
    try:
        # Get all documents with student and application details
        documents_response = db.client.table('documents').select('*').execute()
        all_documents = documents_response.data if documents_response.data else []
        
        print(f"DEBUG: Found {len(all_documents)} total documents")
        
        # Group documents by app_id
        students_docs = {}
        
        for doc in all_documents:
            app_id = doc.get('app_id')
            student_id = doc.get('student_id')
            
            print(f"DEBUG: Processing doc - app_id: {app_id}, student_id: {student_id}")
            
            # Skip if no app_id
            if not app_id:
                print(f"DEBUG: Skipping doc with no app_id")
                continue
            
            # Use app_id as the key for grouping
            if app_id not in students_docs:
                # Get student_id from admission_applications if not in document
                if not student_id or student_id == 'None':
                    try:
                        app_data = db.select('admission_applications', filters={'app_id': app_id})
                        if app_data:
                            student_id = app_data[0].get('student_id')
                            print(f"DEBUG: Got student_id {student_id} from admission_applications")
                    except Exception as e:
                        print(f"DEBUG: Error getting app data: {e}")
                        continue
                
                if not student_id or student_id == 'None':
                    print(f"DEBUG: No valid student_id for app_id {app_id}")
                    continue
                
                # Get student details
                try:
                    student_data = db.select('students', filters={'id': int(student_id)})
                    student = student_data[0] if student_data else None
                    print(f"DEBUG: Student data: {student.get('full_name') if student else 'None'}")
                except Exception as e:
                    print(f"DEBUG: Error getting student: {e}")
                    student = None
                
                if not student:
                    print(f"DEBUG: Student not found for student_id {student_id}")
                    # Still create entry with N/A values
                    student = {}
                
                students_docs[app_id] = {
                    'student_id': student_id,
                    'app_id': app_id,
                    'student_name': student.get('full_name') or student.get('name') or f'Student ID: {student_id}',
                    'unique_id': student.get('unique_id') or 'N/A',
                    'email': student.get('email') or 'N/A',
                    'phone': student.get('phone') or 'N/A',
                    'documents': {}  # Dictionary to hold documents by type
                }
            
            # Add document to the documents dictionary by type
            doc_type = doc.get('document_type', 'Unknown')
            students_docs[app_id]['documents'][doc_type] = {
                'id': doc.get('id'),
                'document_url': doc.get('document_url'),
                'file_size': doc.get('file_size', 0),
                'created_at': doc.get('created_at'),
                'uploaded_by': doc.get('uploaded_by', 'N/A')
            }
        
        # Convert to list for template
        documents_list = list(students_docs.values())
        
        # Sort by app_id for better organization
        documents_list.sort(key=lambda x: x.get('app_id', 0) or 0)
        
        # Define all possible document types
        document_types = [
            '10th_Mark_Sheet',
            '12th_Mark_Sheet',
            'Community_Certificate',
            'Passport_Photo',
            'Transfer_Certificate',
            'FG_Certificate'
        ]
        
        return render_template('admin/documents_management.html', 
                             user=user,
                             documents=documents_list,
                             document_types=document_types,
                             total_documents=len(all_documents))
    except Exception as e:
        print(f"Error loading documents: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading documents', 'error')
        return render_template('admin/documents_management.html', 
                             user=user,
                             documents=[],
                             document_types=[],
                             total_documents=0)


@admin_bp.route('/admin/delete-document/<int:doc_id>', methods=['DELETE'])
@role_required(['admin', 'super_admin'])
def delete_document(doc_id):
    """Delete a document"""
    try:
        # Get document details
        doc_data = db.select('documents', filters={'id': doc_id})
        if not doc_data:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        doc = doc_data[0]
        app_id = doc.get('app_id')
        document_url = doc.get('document_url')
        file_path = doc.get('document_url', '').split('/Student_files/')[-1] if doc.get('document_url') else None
        
        # Delete from storage bucket
        if file_path:
            try:
                db.client.storage.from_('Student_files').remove([file_path])
            except Exception as e:
                print(f"Error deleting file from bucket: {e}")
        
        # Delete from documents table
        db.delete('documents', {'id': doc_id})
        
        # Update documents count in admission_applications
        remaining_docs = db.select('documents', filters={'app_id': app_id})
        doc_count = len(remaining_docs) if remaining_docs else 0
        
        db.update('admission_applications', 
                 {'documents_count': doc_count},
                 {'app_id': app_id})
        
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    
    except Exception as e:
        print(f"Error deleting document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/get-student-documents/<app_id>', methods=['GET'])
def get_student_documents(app_id):
    """Get documents for a specific student by app_id - used for edit modal"""
    try:
        # Convert app_id to integer
        try:
            app_id = int(app_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid app_id',
                'documents': {}
            }), 400
        
        print(f"DEBUG: Fetching documents for app_id: {app_id}")
        
        # Get all documents for this app_id
        docs_response = db.select('documents', filters={'app_id': app_id})
        documents = docs_response if docs_response else []
        
        print(f"DEBUG: Found {len(documents)} documents for app_id {app_id}")
        
        # Organize documents by type
        docs_by_type = {}
        for doc in documents:
            doc_type = doc.get('document_type', 'Unknown')
            docs_by_type[doc_type] = {
                'id': doc.get('id'),
                'document_url': doc.get('document_url'),
                'created_at': doc.get('created_at')
            }
            print(f"DEBUG: Added {doc_type} to response")
        
        print(f"DEBUG: Returning documents: {docs_by_type}")
        
        return jsonify({
            'success': True,
            'documents': docs_by_type
        })
    except Exception as e:
        print(f"Error getting student documents: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'documents': {}
        }), 500


@admin_bp.route('/counselling')
@check_module_access('counselling')
@role_required(['admin', 'super_admin'])
def counselling_list():
    """List students eligible for counselling (documents submitted)."""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'

    pending_students = []
    completed_students = []
    
    try:
        apps_response = db.client.table('admission_applications')\
            .select('app_id,student_id,documents_count,step3_completed,created_at')\
            .gt('documents_count', 0).order('created_at', desc=True).execute()
        apps = apps_response.data if apps_response and apps_response.data else []
    except Exception as e:
        print(f"Error fetching admission applications: {e}")
        apps = []

    for app in apps:
        student_id = app.get('student_id')
        student_data = db.select('students', filters={'id': student_id})
        student = student_data[0] if student_data else {}

        counselling_record = db.select('counselling_records', filters={'app_id': app.get('app_id')})
        counselling_record = counselling_record[0] if counselling_record else None

        # Fetch full admission_application row to get step-1 counselling details
        admission_app = db.select('admission_applications', filters={'app_id': app.get('app_id')})
        admission_app = admission_app[0] if admission_app and isinstance(admission_app, list) and len(admission_app) > 0 else {}

        student_info = {
            'app_id': app.get('app_id'),
            'student_id': student_id,
            'student_name': student.get('full_name') or student.get('name') or 'N/A',
            'unique_id': student.get('unique_id') or 'N/A',
            'documents_count': app.get('documents_count') or 0,
            'step3_completed': app.get('step3_completed') or False,
            # Step-1 counselling/application flags stored on admission_applications
            'applied_for_counselling': admission_app.get('applied_for_counselling') if admission_app else False,
            'counselling_application_number': admission_app.get('counselling_application_number') if admission_app else None,
            'counselling_applied_at': admission_app.get('counselling_applied_at') if admission_app else None,
        }

        if counselling_record:
            # Get allotted department name
            dept_data = db.select('departments', filters={'id': counselling_record.get('allotted_dept_id')})
            dept_name = dept_data[0].get('dept_name') if dept_data else 'N/A'
            
            student_info.update({
                'quota_type': counselling_record.get('quota_type'),
                'allotted_dept': dept_name,
                'allotment_order_url': counselling_record.get('allotment_order_url'),
                'consortium_number': counselling_record.get('consortium_number'),
            })
            completed_students.append(student_info)
        else:
            pending_students.append(student_info)

    return render_template('admin/counselling_list.html',
                          user=user,
                          pending_students=pending_students,
                          completed_students=completed_students)


@admin_bp.route('/counselling/apply/<app_id>', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
@check_module_access('counselling')
def counselling_apply(app_id):
    """Step-1: Mark application as applied for counselling and store application number/date."""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'

    # Load existing application if present
    app_rows = db.select('admission_applications', filters={'app_id': app_id})
    app_row = app_rows[0] if app_rows and len(app_rows) > 0 else {}

    if request.method == 'GET':
        return render_template('admin/counselling_apply.html', app=app_row)

    # POST: save step-1 fields (support GQ / MQ / both)
    # Checkboxes: applied_gq, applied_mq
    applied_gq = True if request.form.get('applied_gq') == 'on' else False
    applied_mq = True if request.form.get('applied_mq') == 'on' else False

    # GQ fields
    gq_application_number = request.form.get('gq_application_number') or request.form.get('application_number')
    gq_applied_at = request.form.get('gq_applied_at') or request.form.get('applied_at') or (datetime.utcnow().isoformat() if applied_gq else None)
    # GQ round (1,2,3,4,supplementary)
    gq_round = request.form.get('gq_round')

    # MQ fields
    mq_consortium_number = request.form.get('mq_consortium_number')
    mq_applied_at = request.form.get('mq_applied_at') or (datetime.utcnow().isoformat() if applied_mq else None)

    update_payload = {
        'applied_for_counselling': True,
        'applied_gq': applied_gq,
        'gq_application_number': gq_application_number if applied_gq else None,
        'gq_applied_at': gq_applied_at if applied_gq else None,
        'gq_round': gq_round if applied_gq and gq_round else None,
        'applied_mq': applied_mq,
        'mq_consortium_number': mq_consortium_number if applied_mq else None,
        'mq_applied_at': mq_applied_at if applied_mq else None,
    }

    try:
        updated = db.update('admission_applications', filters={'app_id': app_id}, data=update_payload)
        if not updated:
            insert_payload = dict(update_payload)
            insert_payload['app_id'] = app_id
            db.insert('admission_applications', insert_payload)
    except Exception:
        insert_payload = dict(update_payload)
        insert_payload['app_id'] = app_id
        db.insert('admission_applications', insert_payload)

    flash('Counselling application (step-1) recorded.', 'success')
    return redirect(url_for('admin.counselling_list'))


@admin_bp.route('/counselling/<int:app_id>', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
def counselling_form(app_id):
    """Counselling step: quota, allotment, and order upload."""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'

    app_data = db.select('admission_applications', filters={'app_id': app_id})
    if not app_data:
        flash('Application not found', 'error')
        return redirect(url_for('admin.counselling_list'))

    app_data = app_data[0]
    student_id = app_data.get('student_id')
    student_data = db.select('students', filters={'id': student_id})
    student = student_data[0] if student_data else {}

    departments = db.select('departments')
    existing_record = db.select('counselling_records', filters={'app_id': app_id})
    existing_record = existing_record[0] if existing_record else None

    if request.method == 'POST':
        try:
            quota_type = request.form.get('quota_type')
            allotted_dept_id = request.form.get('allotted_dept_id')
            allotment_order_number = request.form.get('allotment_order_number')
            consortium_number = request.form.get('consortium_number')

            if not quota_type or not allotted_dept_id:
                flash('Quota type and allotted department are required', 'error')
                return redirect(url_for('admin.counselling_form', app_id=app_id))

            allotment_order_url = existing_record.get('allotment_order_url') if existing_record else None

            if quota_type == 'GQ':
                if not allotment_order_number:
                    flash('Allotment order number is required for GQ', 'error')
                    return redirect(url_for('admin.counselling_form', app_id=app_id))

                file = request.files.get('allotment_order_pdf')
                if file and file.filename:
                    allowed_extensions = {'pdf'}
                    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    if file_ext not in allowed_extensions:
                        flash('Allotment order must be a PDF file', 'error')
                        return redirect(url_for('admin.counselling_form', app_id=app_id))

                    file.seek(0, 2)
                    file_size = file.tell()
                    file.seek(0)
                    if file_size > 5 * 1024 * 1024:
                        flash('Allotment order PDF must be under 5MB', 'error')
                        return redirect(url_for('admin.counselling_form', app_id=app_id))

                    bucket_name = 'Student_files'
                    file_path = f"student_{student_id}/allotment_order_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.pdf"
                    file_content = file.read()
                    response = db.client.storage.from_(bucket_name).upload(
                        file_path,
                        file_content,
                        {"contentType": file.content_type}
                    )

                    public_url = db.client.storage.from_(bucket_name).get_public_url(file_path)
                    if isinstance(public_url, dict) and 'publicUrl' in public_url:
                        public_url = public_url['publicUrl']
                    
                    # Add download parameter for PDFs
                    if public_url:
                        public_url = f"{public_url}?download"

                    allotment_order_url = public_url
                elif not allotment_order_url:
                    flash('Allotment order PDF is required for GQ', 'error')
                    return redirect(url_for('admin.counselling_form', app_id=app_id))

            if quota_type == 'MQ' and not consortium_number:
                flash('Consortium number is required for MQ', 'error')
                return redirect(url_for('admin.counselling_form', app_id=app_id))

            counselling_data = {
                'app_id': app_id,
                'student_id': student_id,
                'quota_type': quota_type,
                'allotted_dept_id': int(allotted_dept_id),
                'allotment_order_number': allotment_order_number if quota_type == 'GQ' else None,
                'allotment_order_url': allotment_order_url if quota_type == 'GQ' else None,
                'consortium_number': consortium_number if quota_type == 'MQ' else None,
                'updated_at': datetime.now().isoformat()
            }

            if existing_record:
                db.update('counselling_records', counselling_data, {'app_id': app_id})
            else:
                counselling_data['created_at'] = datetime.now().isoformat()
                db.insert('counselling_records', counselling_data)

            flash('Counselling details saved successfully', 'success')
            return redirect(url_for('admin.counselling_list'))

        except Exception as e:
            print(f"Counselling save error: {e}")
            flash('Error saving counselling details', 'error')

    return render_template('admin/counselling_form.html',
                          user=user,
                          student=student,
                          application=app_data,
                          departments=departments,
                          record=existing_record)


@admin_bp.route('/payments')
@role_required(['admin', 'super_admin'])
def payments_list():
    """List students eligible for payment (counselling completed)."""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'

    pending_students = []
    completed_students = []
    
    try:
        # Get all applications with uploaded documents (eligible for payment)
        apps_response = db.client.table('admission_applications')\
            .select('app_id,student_id,documents_count,registration_id,created_at')\
            .gt('documents_count', 0).order('created_at', desc=True).execute()
        apps = apps_response.data if apps_response and apps_response.data else []
    except Exception as e:
        print(f"Error fetching admission applications for payments: {e}")
        apps = []

    for app in apps:
        app_id = app.get('app_id')
        student_id = app.get('student_id')

        # Get student data
        student_data = db.select('students', filters={'id': student_id})
        student = student_data[0] if student_data else {}

        # Get counselling record if present
        counselling_record = db.select('counselling_records', filters={'app_id': app_id})
        counselling_record = counselling_record[0] if counselling_record else None

        if counselling_record:
            dept_data = db.select('departments', filters={'id': counselling_record.get('allotted_dept_id')})
            dept_name = dept_data[0].get('dept_name') if dept_data else 'N/A'
            quota_type = counselling_record.get('quota_type') or 'N/A'
        else:
            dept_name = 'Pending'
            quota_type = 'Pending'

        # Check if payment record exists
        payment_record = db.select('payments', filters={'app_id': app_id})
        payment_record = payment_record[0] if payment_record else None

        student_info = {
            'app_id': app_id,
            'student_id': student_id,
            'student_name': student.get('full_name') or student.get('name') or 'N/A',
            'unique_id': student.get('unique_id') or 'N/A',
            'registration_id': app.get('registration_id') or app.get('application_number') or 'N/A',
            'allotted_dept': dept_name,
            'quota_type': quota_type,
        }

        if payment_record:
            student_info.update({
                'bill_no': payment_record.get('bill_no'),
                'mode_of_payment': payment_record.get('mode_of_payment'),
                'amount': payment_record.get('amount'),
                'upi_id': payment_record.get('upi_id'),
            })
            completed_students.append(student_info)
        else:
            pending_students.append(student_info)

    return render_template('admin/payments_list.html',
                          user=user,
                          pending_students=pending_students,
                          completed_students=completed_students)


@admin_bp.route('/payments/<int:app_id>', methods=['GET', 'POST'])
@role_required(['admin', 'super_admin'])
def payments_form(app_id):
    """Payment details form: bill number, mode of payment, amount."""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Admin'

    app_data = db.select('admission_applications', filters={'app_id': app_id})
    if not app_data:
        flash('Application not found', 'error')
        return redirect(url_for('admin.payments_list'))

    app_data = app_data[0]
    student_id = app_data.get('student_id')
    student_data = db.select('students', filters={'id': student_id})
    student = student_data[0] if student_data else {}

    # Get counselling details
    counselling_data = db.select('counselling_records', filters={'app_id': app_id})
    counselling = counselling_data[0] if counselling_data else {}

    # Determine department name and quota; if counselling not done show Pending
    if counselling and isinstance(counselling, dict) and counselling.get('allotted_dept_id'):
        dept_data = db.select('departments', filters={'id': counselling.get('allotted_dept_id')})
        dept_name = dept_data[0].get('dept_name') if dept_data else 'N/A'
        quota_type = counselling.get('quota_type') or 'N/A'
    else:
        dept_name = 'Pending'
        quota_type = 'Pending'

    # Get existing payment record if any
    existing_record = db.select('payments', filters={'app_id': app_id})
    existing_record = existing_record[0] if existing_record else None

    if request.method == 'POST':
        try:
            bill_no = request.form.get('bill_no', '').strip()
            mode_of_payment = request.form.get('mode_of_payment', '').strip()
            amount = request.form.get('amount', '').strip()
            upi_id = request.form.get('upi_id', '').strip()

            if not bill_no or not mode_of_payment or not amount:
                flash('All payment fields are required', 'error')
                return redirect(url_for('admin.payments_form', app_id=app_id))

            # If payment is via UPI, ensure UPI ID provided
            if mode_of_payment.upper() == 'UPI' and not upi_id:
                flash('UPI ID is required when Mode of Payment is UPI', 'error')
                return redirect(url_for('admin.payments_form', app_id=app_id))

            try:
                amount = float(amount)
            except:
                flash('Invalid amount format', 'error')
                return redirect(url_for('admin.payments_form', app_id=app_id))

            # Ensure bill_no uniqueness (unique constraint in DB)
            existing_by_bill = db.select('payments', filters={'bill_no': bill_no}) or []
            if existing_by_bill:
                # if existing record belongs to different application, reject
                if not existing_record or int(existing_by_bill[0].get('app_id') or 0) != int(app_id):
                    flash('Bill number already exists for another payment', 'error')
                    return redirect(url_for('admin.payments_form', app_id=app_id))

            payment_data = {
                'app_id': app_id,
                'student_id': student_id,
                'bill_no': bill_no,
                'mode_of_payment': mode_of_payment,
                'upi_id': upi_id,
                'amount': amount,
                'created_at': datetime.now().isoformat()
            }

            try:
                if existing_record:
                    payment_data['updated_at'] = datetime.now().isoformat()
                    res = db.update('payments', payment_data, {'app_id': app_id})
                    if res is None:
                        flash('Failed to update payment (DB error). See server logs.', 'error')
                    else:
                        flash('Payment details updated successfully', 'success')
                else:
                    res = db.insert('payments', payment_data)
                    if res is None:
                        flash('Failed to save payment (DB error). See server logs.', 'error')
                    else:
                        flash('Payment details saved successfully', 'success')
            except Exception as e:
                print(f"Unexpected error saving payment: {e}")
                import traceback
                traceback.print_exc()
                flash('Unexpected error saving payment. See server logs.', 'error')

            return redirect(url_for('admin.payments_list'))

        except Exception as e:
            print(f"Payment save error: {e}")
            flash('Error saving payment details', 'error')

    return render_template('admin/payments_form.html',
                          user=user,
                          student=student,
                          application=app_data,
                          counselling=counselling,
                          dept_name=dept_name,
                          quota_type=quota_type,
                          record=existing_record)


@admin_bp.route('/student-profiles')
@role_required(['super_admin'])
def student_profiles():
    """List all students with complete data from all tables"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Super Admin'
    
    # Get all students
    all_students = db.select('students') or []
    
    students_data = []
    for student in all_students:
        student_id = student.get('id')
        
        # Get ALL data from each table
        academic = db.select('academics', filters={'student_id': student_id})
        academic = academic[0] if academic else {}
        
        enquiries = db.select('enquiries', filters={'student_id': student_id}) or []
        
        admissions = db.select('admissions', filters={'student_id': student_id}) or []
        for admission in admissions:
            if admission.get('preferred_dept_id'):
                dept = db.select('departments', filters={'id': admission['preferred_dept_id']})
                admission['preferred_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
            if admission.get('allotted_dept_id'):
                dept = db.select('departments', filters={'id': admission['allotted_dept_id']})
                admission['allotted_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
        
        applications = db.select('admission_applications', filters={'student_id': student_id}) or []
        
        # Documents grouped by type for each application
        documents_by_app = {}
        counselling_records = []
        payments = []
        
        for app in applications:
            app_id = app.get('app_id')
            
            # Get documents and group by type
            app_docs = db.select('documents', filters={'app_id': app_id}) or []
            documents_by_app[app_id] = {}
            for doc in app_docs:
                doc_type = doc.get('document_type', 'Unknown')
                documents_by_app[app_id][doc_type] = {
                    'id': doc.get('id'),
                    'document_url': doc.get('document_url'),
                    'file_size': doc.get('file_size', 0),
                    'created_at': doc.get('created_at'),
                    'uploaded_by': doc.get('uploaded_by', 'N/A')
                }
            
            counselling = db.select('counselling_records', filters={'app_id': app_id}) or []
            for record in counselling:
                if record.get('allotted_dept_id'):
                    dept = db.select('departments', filters={'id': record['allotted_dept_id']})
                    record['dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
                record['app_id'] = app_id
                counselling_records.append(record)
            
            payment = db.select('payments', filters={'app_id': app_id}) or []
            for p in payment:
                p['app_id'] = app_id
                payments.append(p)
        
        students_data.append({
            'student': student,
            'academic': academic,
            'enquiries': enquiries,
            'admissions': admissions,
            'applications': applications,
            'documents_by_app': documents_by_app,
            'counselling': counselling_records,
            'payments': payments
        })
    
    # Fields available for Excel export (columns in the flattened students sheet)
    export_fields = [
        'Student ID','Name','Unique ID','Email','Phone','Gender','DOB',
        'Community','Religion','Status','Accepted By','Accepted At','Created At',
        'HSC School','HSC Percentage','Cutoff','TNEA Eligible','TNEA Average',
        'Enquiries Count','Admissions Count','Applications Count'
    ]

    return render_template('admin/student_profiles.html',
                          user=user,
                          students=students_data,
                          export_fields=export_fields)


@admin_bp.route('/student-profiles/export-excel')
@role_required(['super_admin'])
def student_profiles_export_excel():
    """Export all student profiles to Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
    except ImportError:
        flash('Excel export library not installed. Please install pandas and openpyxl.', 'error')
        return redirect(url_for('admin.student_profiles'))
    
    # Get all students data
    all_students = db.select('students') or []
    
    # Prepare data for Excel
    students_flat = []
    for student in all_students:
        student_id = student.get('id')
        
        academic = db.select('academics', filters={'student_id': student_id})
        academic = academic[0] if academic else {}
        
        enquiries = db.select('enquiries', filters={'student_id': student_id}) or []
        admissions = db.select('admissions', filters={'student_id': student_id}) or []
        applications = db.select('admission_applications', filters={'student_id': student_id}) or []
        
        # Flatten student data
        row = {
            'Student ID': student_id,
            'Name': student.get('full_name') or student.get('name'),
            'Unique ID': student.get('unique_id'),
            'Email': student.get('email'),
            'Phone': student.get('phone'),
            'Gender': student.get('gender'),
            'DOB': student.get('dob'),
            'Community': student.get('community'),
            'Religion': student.get('religion'),
            'Status': student.get('status'),
            'Accepted By': student.get('accepted_by'),
            'Accepted At': student.get('accepted_at'),
            'Created At': student.get('created_at'),
            # Academic
            'HSC School': academic.get('hsc_school_name'),
            'HSC Percentage': academic.get('hsc_percentage'),
            'Cutoff': academic.get('cutoff'),
            'TNEA Eligible': academic.get('tnea_eligible'),
            'TNEA Average': academic.get('tnea_average'),
            # Counts
            'Enquiries Count': len(enquiries),
            'Admissions Count': len(admissions),
            'Applications Count': len(applications),
        }
        students_flat.append(row)
    
    # Create Excel file with multiple sheets
    output = BytesIO()
    # Respect optional 'fields' query parameter (comma separated human-friendly column names)
    fields_param = request.args.get('fields')

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Students sheet
        df_students = pd.DataFrame(students_flat)
        # If user supplied a subset of fields, filter the df to those columns (if present)
        if fields_param:
            requested = [f.strip() for f in fields_param.split(',') if f.strip()]
            # Keep only columns that actually exist
            available = [c for c in requested if c in df_students.columns]
            if available:
                df_students = df_students[available]
        df_students.to_excel(writer, sheet_name='Students', index=False)
        
        # All enquiries
        all_enquiries = db.select('enquiries') or []
        if all_enquiries:
            df_enquiries = pd.DataFrame(all_enquiries)
            df_enquiries.to_excel(writer, sheet_name='Enquiries', index=False)
        
        # All admissions
        all_admissions = db.select('admissions') or []
        if all_admissions:
            df_admissions = pd.DataFrame(all_admissions)
            df_admissions.to_excel(writer, sheet_name='Admissions', index=False)
        
        # All applications
        all_apps = db.select('admission_applications') or []
        if all_apps:
            df_apps = pd.DataFrame(all_apps)
            df_apps.to_excel(writer, sheet_name='Applications', index=False)
        
        # All counselling
        all_counselling = db.select('counselling_records') or []
        if all_counselling:
            df_counselling = pd.DataFrame(all_counselling)
            df_counselling.to_excel(writer, sheet_name='Counselling', index=False)
        
        # All payments
        all_payments = db.select('payments') or []
        if all_payments:
            df_payments = pd.DataFrame(all_payments)
            df_payments.to_excel(writer, sheet_name='Payments', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'student_profiles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


@admin_bp.route('/student-profile/<int:student_id>')
@role_required(['super_admin'])
def student_profile(student_id):
    """View complete student profile with all details"""
    user = get_current_user()
    if user:
        user['role'] = session.get('user_role')
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Super Admin'
    
    # Get student basic info
    student_data = db.select('students', filters={'id': student_id})
    if not student_data:
        flash('Student not found', 'error')
        return redirect(url_for('admin.student_profiles'))
    
    student = student_data[0]
    
    # Get academic details
    academic = db.select('academics', filters={'student_id': student_id})
    academic = academic[0] if academic else {}
    
    # Get enquiries
    enquiries = db.select('enquiries', filters={'student_id': student_id}) or []
    
    # Get admissions/branch assignments
    admissions = db.select('admissions', filters={'student_id': student_id}) or []
    for admission in admissions:
        # Get department names
        if admission.get('preferred_dept_id'):
            dept = db.select('departments', filters={'id': admission['preferred_dept_id']})
            admission['preferred_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
        if admission.get('allotted_dept_id'):
            dept = db.select('departments', filters={'id': admission['allotted_dept_id']})
            admission['allotted_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
    
    # Get applications
    applications = db.select('admission_applications', filters={'student_id': student_id}) or []
    
    # Get documents for each application
    documents = []
    documents_by_app = {}
    for app in applications:
        app_id = app.get('app_id')
        app_docs = db.select('documents', filters={'app_id': app_id}) or []
        documents_by_app[app_id] = {}
        for doc in app_docs:
            doc['app_id'] = app_id
            documents.append(doc)
            # Group by document type
            doc_type = doc.get('document_type', 'Unknown')
            documents_by_app[app_id][doc_type] = {
                'id': doc.get('id'),
                'document_url': doc.get('document_url'),
                'file_size': doc.get('file_size', 0),
                'created_at': doc.get('created_at'),
                'uploaded_by': doc.get('uploaded_by', 'N/A')
            }
    
    # Get counselling records
    counselling_records = []
    for app in applications:
        app_id = app.get('app_id')
        counselling = db.select('counselling_records', filters={'app_id': app_id}) or []
        for record in counselling:
            if record.get('allotted_dept_id'):
                dept = db.select('departments', filters={'id': record['allotted_dept_id']})
                record['dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
            record['app_id'] = app_id
            counselling_records.append(record)
    
    # Get payments
    payments = []
    for app in applications:
        app_id = app.get('app_id')
        payment = db.select('payments', filters={'app_id': app_id}) or []
        for p in payment:
            p['app_id'] = app_id
            payments.append(p)
    
    profile_data = {
        'student': student,
        'academic': academic,
        'enquiries': enquiries,
        'admissions': admissions,
        'applications': applications,
        'documents': documents,
        'documents_by_app': documents_by_app,
        'counselling': counselling_records,
        'payments': payments
    }
    
    return render_template('admin/student_profile_view.html',
                          user=user,
                          profile=profile_data)


@admin_bp.route('/student-profile/<int:student_id>/pdf')
@role_required(['super_admin'])
def student_profile_pdf(student_id):
    """Generate PDF of student profile"""
    from flask import make_response
    from io import BytesIO
    from xhtml2pdf import pisa
    
    # Get student data (same as student_profile route)
    student_data = db.select('students', filters={'id': student_id})
    if not student_data:
        flash('Student not found', 'error')
        return redirect(url_for('admin.student_profiles'))
    
    student = student_data[0]
    academic = db.select('academics', filters={'student_id': student_id})
    academic = academic[0] if academic else {}
    enquiries = db.select('enquiries', filters={'student_id': student_id}) or []
    admissions = db.select('admissions', filters={'student_id': student_id}) or []
    
    for admission in admissions:
        if admission.get('preferred_dept_id'):
            dept = db.select('departments', filters={'id': admission['preferred_dept_id']})
            admission['preferred_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
        if admission.get('optional_dept_id'):
            dept = db.select('departments', filters={'id': admission['optional_dept_id']})
            admission['optional_dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
    
    applications = db.select('admission_applications', filters={'student_id': student_id}) or []
    documents = []
    documents_by_app = {}
    counselling_records = []
    payments = []
    
    for app in applications:
        app_id = app.get('app_id')
        app_docs = db.select('documents', filters={'app_id': app_id}) or []
        documents_by_app[app_id] = {}
        for doc in app_docs:
            doc['app_id'] = app_id
            documents.append(doc)
            # Group by document type
            doc_type = doc.get('document_type', 'Unknown')
            documents_by_app[app_id][doc_type] = {
                'id': doc.get('id'),
                'document_url': doc.get('document_url'),
                'file_size': doc.get('file_size', 0),
                'created_at': doc.get('created_at'),
                'uploaded_by': doc.get('uploaded_by', 'N/A')
            }
        
        counselling = db.select('counselling_records', filters={'app_id': app_id}) or []
        for record in counselling:
            if record.get('allotted_dept_id'):
                dept = db.select('departments', filters={'id': record['allotted_dept_id']})
                record['dept_name'] = dept[0].get('dept_name') if dept else 'N/A'
            record['app_id'] = app_id
            counselling_records.append(record)
        
        payment = db.select('payments', filters={'app_id': app_id}) or []
        for p in payment:
            p['app_id'] = app_id
            payments.append(p)
    
    profile_data = {
        'student': student,
        'academic': academic,
        'enquiries': enquiries,
        'admissions': admissions,
        'applications': applications,
        'documents': documents,
        'documents_by_app': documents_by_app,
        'counselling': counselling_records,
        'payments': payments
    }
    
    # Render HTML template for PDF
    html = render_template('admin/student_profile_pdf.html', profile=profile_data)
    
    # Generate PDF using xhtml2pdf
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    
    if pisa_status.err:
        flash('Error generating PDF', 'error')
        return redirect(url_for('admin.student_profile', student_id=student_id))
    
    # Create response
    pdf_buffer.seek(0)
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=student_profile_{student.get("unique_id", student_id)}.pdf'
    
    return response


@admin_bp.route('/dashboard/search')
@role_required(['super_admin'])
def dashboard_search():
    """Search across all tables in super admin dashboard"""
    table_name = request.args.get('table', '').lower()
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Map table names to display names and searchable fields
    table_mappings = {
        'enquiries': {'table': 'enquiries', 'search_fields': ['phone', 'email']},
        'applications': {'table': 'admission_applications', 'search_fields': ['app_id', 'status']},
        'counselling': {'table': 'counselling_records', 'search_fields': ['consortium_number']},
        'payments': {'table': 'payments', 'search_fields': ['amount', 'status']},
        'documents': {'table': 'documents', 'search_fields': ['status', 'doc_type']},
        'students': {'table': 'students', 'search_fields': ['full_name', 'email', 'phone']},
        'admissions': {'table': 'admissions', 'search_fields': ['status']},
        'users': {'table': 'users', 'search_fields': ['email', 'first_name', 'last_name']},
    }
    
    if table_name not in table_mappings:
        return jsonify({'error': 'Invalid table', 'results': []}), 400
    
    try:
        table_config = table_mappings[table_name]
        actual_table = table_config['table']
        
        # Get all data from table
        data = db.select(actual_table) or []
        
        # Filter based on search query
        filtered_data = []
        if search_query:
            for record in data:
                for field in table_config['search_fields']:
                    value = str(record.get(field, '')).lower()
                    if search_query.lower() in value:
                        filtered_data.append(record)
                        break
        else:
            filtered_data = data
        
        # Pagination
        total = len(filtered_data)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_data = filtered_data[start:end]
        
        return jsonify({
            'success': True,
            'table': table_name,
            'results': paginated_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        print(f"Dashboard search error: {str(e)}")
        return jsonify({'error': str(e), 'results': []}), 500
