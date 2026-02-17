from database.supabase_config import db
from datetime import datetime

class UserModel:
    """User Management Model"""
    
    @staticmethod
    def get_user_by_email(email: str):
        """Get user by email"""
        try:
            users = db.select('users', filters={'email': email})
            count = len(users) if users else 0
            print(f"get_user_by_email: email={email}, returned_count={count}")
            return users[0] if users else None
        except Exception as e:
            print(f"get_user_by_email: error querying email={email}: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int):
        """Get user by ID"""
        users = db.select('users', filters={'user_id': user_id})
        return users[0] if users else None
    
    @staticmethod
    def verify_login(email: str, password: str):
        """Verify user login credentials"""
        user = UserModel.get_user_by_email(email)

        # Debug logs to help diagnose login failures (will appear in server logs).
        try:
            user_found = bool(user)
            password_match = bool(user and user.get('password') == password)
            is_active = bool(user and user.get('is_active'))
            print(f"verify_login: email={email}, user_found={user_found}, password_match={password_match}, is_active={is_active}")
        except Exception as e:
            print("verify_login: error while logging debug info:", e)

        if user and user.get('password') == password and user.get('is_active'):
            return user
        return None
    
    @staticmethod
    def get_user_role(user_id: int):
        """Get user's role information"""
        users = db.select('users', filters={'user_id': user_id})
        if users:
            user = users[0]
            roles = db.select('roles', filters={'role_id': user['role_id']})
            return roles[0] if roles else None
        return None
    
    @staticmethod
    def create_user(employee_id: str, email: str, password: str, first_name: str, 
                    last_name: str, role_id: int, phone: str = None):
        """Create new user"""
        data = {
            'employee_id': employee_id,
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'role_id': role_id,
            'is_active': True,
            'created_at': datetime.now().isoformat()
        }
        return db.insert('users', data)
    
    @staticmethod
    def update_last_login(user_id: int):
        """Update user's last login timestamp"""
        return db.update('users', 
                        {'last_login': datetime.now().isoformat()},
                        {'user_id': user_id})
    
    @staticmethod
    def get_all_users():
        """Get all users with role information"""
        return db.select('users')


class StudentModel:
    """Student Management Model"""
    
    @staticmethod
    def create_student(full_name: str, email: str, phone: str, **kwargs):
        """Create new student"""
        data = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'whatsapp_number': kwargs.get('whatsapp_number'),
            'date_of_birth': kwargs.get('date_of_birth'),
            'gender': kwargs.get('gender'),
            'community': kwargs.get('community'),
            'father_name': kwargs.get('father_name'),
            'mother_name': kwargs.get('mother_name'),
            'permanent_address': kwargs.get('permanent_address'),
            'city': kwargs.get('city'),
            'state': kwargs.get('state'),
            'pincode': kwargs.get('pincode'),
            'created_at': datetime.now().isoformat()
        }
        return db.insert('students', data)
    
    @staticmethod
    def get_student_by_id(student_id: int):
        """Get student by ID"""
        students = db.select('students', filters={'student_id': student_id})
        return students[0] if students else None
    
    @staticmethod
    def get_student_by_email(email: str):
        """Get student by email"""
        students = db.select('students', filters={'email': email})
        return students[0] if students else None
    
    @staticmethod
    def update_student(student_id: int, data: dict):
        """Update student information"""
        data['updated_at'] = datetime.now().isoformat()
        return db.update('students', data, {'student_id': student_id})


class AcademicModel:
    """Academic Details Management"""
    
    @staticmethod
    def add_academic_details(student_id: int, school_name: str, board: str, 
                            exam_year: int, maths: float, physics: float, 
                            chemistry: float):
        """Add academic details for student"""
        total = maths + physics + chemistry
        percentage = (total / 300) * 100
        
        data = {
            'student_id': student_id,
            'school_name': school_name,
            'board': board,
            'exam_year': exam_year,
            'maths_marks': maths,
            'physics_marks': physics,
            'chemistry_marks': chemistry,
            'total_marks': total,
            'percentage': percentage,
            'created_at': datetime.now().isoformat()
        }
        return db.insert('academic_details', data)
    
    @staticmethod
    def get_academic_details(student_id: int):
        """Get academic details for student"""
        details = db.select('academic_details', filters={'student_id': student_id})
        return details[0] if details else None


class AdmissionApplicationModel:
    """Admission Application Management"""
    
    @staticmethod
    def create_application(student_id: int, academic_id: int):
        """Create new admission application"""
        # Generate registration ID
        registration_id = f"ADM-{datetime.now().strftime('%Y')}-{student_id}"
        
        data = {
            'student_id': student_id,
            'registration_id': registration_id,
            'academic_id': academic_id,
            'application_status': 'step1',
            'step1_completed': False,
            'step2_completed': False,
            'step3_completed': False,
            'admission_status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        return db.insert('admission_applications', data)
    
    @staticmethod
    def get_application(app_id: int):
        """Get application by ID"""
        apps = db.select('admission_applications', filters={'app_id': app_id})
        return apps[0] if apps else None
    
    @staticmethod
    def get_student_application(student_id: int):
        """Get application for student"""
        apps = db.select('admission_applications', filters={'student_id': student_id})
        return apps[0] if apps else None
    
    @staticmethod
    def update_application_step(app_id: int, step: int, primary_dept_id: int = None, 
                               secondary_dept_id: int = None):
        """Update application step completion"""
        data = {}
        
        if step == 1:
            data['step1_completed'] = True
            data['application_status'] = 'step2'
        elif step == 2:
            data['step2_completed'] = True
            data['primary_dept_id'] = primary_dept_id
            data['secondary_dept_id'] = secondary_dept_id
            data['application_status'] = 'step3'
        elif step == 3:
            data['step3_completed'] = True
            data['application_status'] = 'submitted'
            data['admission_status'] = 'under_review'
        
        data['updated_at'] = datetime.now().isoformat()
        return db.update('admission_applications', data, {'app_id': app_id})
    
    @staticmethod
    def get_all_applications(filters: dict = None):
        """Get all applications with optional filters"""
        return db.select('admission_applications', filters=filters)
    
    @staticmethod
    def allocate_department(app_id: int, dept_id: int, category: str):
        """Allocate department to student"""
        data = {
            'allocated_dept_id': dept_id,
            'allocated_category': category,
            'admission_status': 'allocated',
            'updated_at': datetime.now().isoformat()
        }
        return db.update('admission_applications', data, {'app_id': app_id})


class EnquiryModel:
    """Enquiry Management Model"""
    
    @staticmethod
    def create_enquiry(student_id: int = None, student_name: str = None, whatsapp_number: str = None,
                       email: str = None, subject: str = None, preferred_course: str = None,
                       source: str = None, created_by: int = None):
        """Create new enquiry matching `public.enquiries` schema."""
        data = {
            'student_id': student_id,
            'student_name': student_name,
            'whatsapp_number': whatsapp_number,
            'email': email,
            'subject': subject,
            'preferred_course': preferred_course,
            'source': source,
            'created_by': created_by,
            'status': 'open',
            'created_at': datetime.now().isoformat()
        }
        return db.insert('enquiries', data)
    
    @staticmethod
    def get_enquiry(enquiry_id: int):
        """Get enquiry by ID"""
        enquiries = db.select('enquiries', filters={'id': enquiry_id})
        return enquiries[0] if enquiries else None
    
    @staticmethod
    def get_all_enquiries(filters: dict = None):
        """Get all enquiries with optional filters"""
        return db.select('enquiries', filters=filters)
    
    @staticmethod
    def update_enquiry_status(enquiry_id: int, status: str):
        """Update enquiry status (only fields present in schema)."""
        data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        return db.update('enquiries', data, {'id': enquiry_id})


class DepartmentModel:
    """Department Management"""
    
    @staticmethod
    def get_all_departments():
        """Get all departments"""
        return db.select('departments')
    
    @staticmethod
    def get_department(dept_id: int):
        """Get department by ID"""
        depts = db.select('departments', filters={'dept_id': dept_id})
        return depts[0] if depts else None


class SeatModel:
    """Seat Management"""
    
    @staticmethod
    def get_seats_by_department(dept_id: int, academic_year: str):
        """Get seats for department in academic year"""
        seats = db.select('seats', filters={'dept_id': dept_id, 'academic_year': academic_year})
        return seats[0] if seats else None
    
    @staticmethod
    def get_all_seats(academic_year: str):
        """Get all seats for academic year"""
        return db.select('seats', filters={'academic_year': academic_year})
