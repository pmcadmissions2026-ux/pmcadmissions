from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from auth.decorators import login_required, role_required, get_current_user
from database.models import (
    StudentModel, AcademicModel, AdmissionApplicationModel, 
    EnquiryModel, DepartmentModel
)
from database.supabase_config import db

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/step1', methods=['GET', 'POST'])
@login_required
def step1():
    """Step 1: Student Enquiry Form"""
    if request.method == 'POST':
        # Get current user from session
        email = session.get('user_email')
        
        # Create or update student
        full_name = request.form.get('full_name')
        phone = request.form.get('whatsapp_number')
        father_name = request.form.get('father_name')
        mother_name = request.form.get('mother_name')
        
        # Check if student exists
        existing_student = StudentModel.get_student_by_email(email)
        
        if existing_student:
            student_id = existing_student['student_id']
            StudentModel.update_student(student_id, {
                'full_name': full_name,
                'phone': phone,
                'whatsapp_number': request.form.get('whatsapp_number'),
                'father_name': father_name,
                'mother_name': mother_name
            })
        else:
            result = StudentModel.create_student(
                full_name=full_name,
                email=email,
                phone=phone,
                whatsapp_number=request.form.get('whatsapp_number'),
                father_name=father_name,
                mother_name=mother_name
            )
            if result:
                student_id = result[0]['student_id']
            else:
                flash('Error creating student record', 'error')
                return redirect(url_for('student.step1'))
        
        # Add academic details
        maths = float(request.form.get('maths_marks', 0))
        physics = float(request.form.get('physics_marks', 0))
        chemistry = float(request.form.get('chemistry_marks', 0))
        
        academic_result = AcademicModel.add_academic_details(
            student_id=student_id,
            school_name=request.form.get('school_name'),
            board=request.form.get('board'),
            exam_year=int(request.form.get('exam_year', 0)),
            maths=maths,
            physics=physics,
            chemistry=chemistry
        )
        
        if academic_result:
            academic_id = academic_result[0]['academic_id']
            
            # Create admission application
            app_result = AdmissionApplicationModel.create_application(student_id, academic_id)
            if app_result:
                app_id = app_result[0]['app_id']
                
                # Mark step1 as completed
                AdmissionApplicationModel.update_application_step(app_id, 1)
                
                flash('Step 1 completed successfully', 'success')
                return redirect(url_for('student.step2', app_id=app_id))
        
        flash('Error saving academic details', 'error')
        return redirect(url_for('student.step1'))
    
    return render_template('student/step1.html')

@student_bp.route('/step2', methods=['GET', 'POST'])
@login_required
def step2():
    """Step 2: Branch Selection"""
    app_id = request.args.get('app_id')
    
    if not app_id:
        flash('Application ID not found', 'error')
        return redirect(url_for('student.step1'))
    
    # Get application details
    application = AdmissionApplicationModel.get_application(app_id)
    if not application or application['student_id'] != session.get('student_id'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('student.step1'))
    
    if request.method == 'POST':
        primary_dept_id = request.form.get('primary_dept_id')
        secondary_dept_id = request.form.get('secondary_dept_id')
        
        if not primary_dept_id:
            flash('Please select a primary department', 'error')
            return redirect(url_for('student.step2', app_id=app_id))
        
        # Update application with department selections
        AdmissionApplicationModel.update_application_step(
            app_id, 2, 
            primary_dept_id=int(primary_dept_id),
            secondary_dept_id=int(secondary_dept_id) if secondary_dept_id else None
        )
        
        flash('Step 2 completed successfully', 'success')
        return redirect(url_for('student.step3', app_id=app_id))
    
    # Get departments
    departments = DepartmentModel.get_all_departments()
    
    return render_template('student/step2.html', 
                          application=application, 
                          departments=departments,
                          app_id=app_id)

@student_bp.route('/step3', methods=['GET', 'POST'])
@login_required
def step3():
    """Step 3: Application Filing Summary & Submit"""
    app_id = request.args.get('app_id')
    
    if not app_id:
        flash('Application ID not found', 'error')
        return redirect(url_for('student.step1'))
    
    # Get application details
    application = AdmissionApplicationModel.get_application(app_id)
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('student.step1'))
    
    # Get student details
    student = StudentModel.get_student_by_id(application['student_id'])
    
    if request.method == 'POST':
        # Mark step 3 as completed and submit application
        AdmissionApplicationModel.update_application_step(app_id, 3)
        
        # Log audit trail
        db.insert('audit_log', {
            'user_id': session.get('user_id'),
            'action': 'Application submitted',
            'table_name': 'admission_applications',
            'record_id': int(app_id),
            'ip_address': request.remote_addr
        })
        
        flash('Application submitted successfully! Your application is under review.', 'success')
        return redirect(url_for('student.application_status', app_id=app_id))
    
    # Get academic details
    academic = AcademicModel.get_academic_details(application['student_id'])
    
    # Get department details
    primary_dept = None
    secondary_dept = None
    if application['primary_dept_id']:
        primary_dept = DepartmentModel.get_department(application['primary_dept_id'])
    if application['secondary_dept_id']:
        secondary_dept = DepartmentModel.get_department(application['secondary_dept_id'])
    
    return render_template('student/step3.html',
                          application=application,
                          student=student,
                          academic=academic,
                          primary_dept=primary_dept,
                          secondary_dept=secondary_dept,
                          app_id=app_id)

@student_bp.route('/application-status')
@login_required
def application_status():
    """View application status"""
    app_id = request.args.get('app_id')
    
    if not app_id:
        flash('Application ID not found', 'error')
        return redirect(url_for('student.step1'))
    
    application = AdmissionApplicationModel.get_application(app_id)
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('student.step1'))
    
    return render_template('student/application_status.html', application=application)

@student_bp.route('/enquiry', methods=['GET', 'POST'])
def enquiry():
    """Create enquiry"""
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        subject = request.form.get('query_subject')
        description = request.form.get('query_description')
        
        if not all([full_name, phone, email, subject, description]):
            flash('All fields are required', 'error')
            return redirect(url_for('student.enquiry'))
        
        try:
            # Create enquiry and capture the created record/ID
            result = EnquiryModel.create_enquiry(full_name, phone, email, subject, description)

            # result expected to be list-like from DB insert; try to extract id
            enquiry_id = None
            if isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], dict):
                enquiry_id = result[0].get('id') or result[0].get('enquiry_id')
            elif isinstance(result, dict):
                enquiry_id = result.get('id') or result.get('enquiry_id')

            flash('Enquiry submitted successfully! We will contact you soon.', 'success')

            # Send notification to student via server-side SMTP/SendGrid (EmailJS removed)

            # Attempt to fetch student unique_id from students table
            student_unique_id = 'N/A'
            try:
                student = StudentModel.get_student_by_email(email)
                if student:
                    student_unique_id = student.get('unique_id') or student.get('student_unique_id') or 'N/A'
            except Exception:
                current_app.logger.exception('Failed to lookup student by email')

            try:
                from utils.email_helper import send_email_smtp
                from utils.sendgrid_helper import send_email_sendgrid

                subject_line = f"Enquiry Received - {student_unique_id}"

                # Render HTML and plain-text email bodies from templates
                html_body = render_template('emails/enquiry.html', full_name=full_name, unique_id=student_unique_id, subject=subject, description=description, college_name=current_app.config.get('COLLEGE_NAME'))
                text_body = render_template('emails/enquiry.txt', full_name=full_name, unique_id=student_unique_id, subject=subject, description=description, college_name=current_app.config.get('COLLEGE_NAME'))

                to_addr = email
                smtp_sent = send_email_smtp(subject_line, text_body, to_addr, from_name=full_name, reply_to=email, html_body=html_body)
                if smtp_sent:
                    flash('Enquiry saved and notification sent via SMTP.', 'success')
                else:
                    try:
                        sg_sent = send_email_sendgrid(subject_line, text_body, to_addr, from_email=None, from_name=full_name, reply_to=email, html_body=html_body)
                        if sg_sent:
                            flash('Enquiry saved and notification sent via SendGrid fallback.', 'success')
                        else:
                            flash('Enquiry saved but confirmation email failed to send. We will retry.', 'error')
                    except Exception:
                        current_app.logger.exception('SendGrid fallback failed')
                        flash('Enquiry saved but confirmation email failed to send. We will retry.', 'error')
            except Exception:
                current_app.logger.exception('Failed to send enquiry email')
                flash('Enquiry saved but confirmation email failed to send. We will retry.', 'error')

            return redirect(url_for('student.enquiry'))
        except Exception as e:
            flash(f'Error submitting enquiry: {str(e)}', 'error')
            return redirect(url_for('student.enquiry'))
    
    return render_template('student/enquiry.html')
