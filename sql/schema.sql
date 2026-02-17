-- ============================================
-- PMC ADMISSION CONTROL SYSTEM - DATABASE SCHEMA
-- ============================================

-- 1. ROLES TABLE
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default roles
INSERT INTO roles (role_name, description) VALUES
('super_admin', 'Super Administrator - Full system access'),
('admin', 'Administrator - Manages admissions and staff'),
('admission_coordinator', 'Admission Coordinator - Manages student applications'),
('student', 'Student - Can fill admission forms');

-- 2. USERS TABLE (Staff/Admin)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role_id INTEGER NOT NULL REFERENCES roles(role_id),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. DEPARTMENTS TABLE
CREATE TABLE departments (
    dept_id SERIAL PRIMARY KEY,
    dept_code VARCHAR(20) UNIQUE NOT NULL,
    dept_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50),
    description TEXT,
    hod_name VARCHAR(100),
    hod_email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert departments
INSERT INTO departments (dept_code, dept_name, short_name) VALUES
('AERO', 'Aeronautical Engineering', 'AERO'),
('AI', 'Artificial Intelligence', 'AI'),
('CSBS', 'Computer Science & Business Systems', 'CSBS'),
('CSE', 'Computer Science & Engineering', 'CSE'),
('CIVIL', 'Civil Engineering', 'CIVIL'),
('EEE', 'Electrical & Electronics Engineering', 'EEE'),
('IT', 'Information Technology', 'IT'),
('ECE', 'Electronics & Communication Engineering', 'ECE'),
('MCO', 'Mechatronics Engineering', 'MCO'),
('MECH', 'Mechanical Engineering', 'MECH'),
('ML', 'Machine Learning', 'ML'),
('CH', 'Chemical Engineering', 'CH');

-- 4. SEATS TABLE
CREATE TABLE seats (
    seat_id SERIAL PRIMARY KEY,
    dept_id INTEGER NOT NULL REFERENCES departments(dept_id),
    academic_year VARCHAR(20) NOT NULL,
    mq_seats INTEGER DEFAULT 0,
    gq_seats INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dept_id, academic_year)
);

-- Insert seat information for 2025-2026
INSERT INTO seats (dept_id, academic_year, mq_seats, gq_seats) VALUES
(1, '2025-2026', 4, 56),
(2, '2025-2026', 15, 111),
(3, '2025-2026', 5, 58),
(4, '2025-2026', 15, 111),
(5, '2025-2026', 2, 58),
(6, '2025-2026', 3, 60),
(7, '2025-2026', 12, 114),
(8, '2025-2026', 10, 116),
(9, '2025-2026', 3, 60),
(10, '2025-2026', 3, 117),
(11, '2025-2026', 10, 53),
(12, '2025-2026', 2, 58);

-- 5. STUDENTS TABLE
CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    registration_id VARCHAR(50) UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    whatsapp_number VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(10),
    community VARCHAR(50),
    father_name VARCHAR(100),
    mother_name VARCHAR(100),
    permanent_address TEXT,
    city VARCHAR(50),
    state VARCHAR(50),
    pincode VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. ACADEMIC_DETAILS TABLE
CREATE TABLE academic_details (
    academic_id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    school_name VARCHAR(200),
    board VARCHAR(50),
    exam_year INTEGER,
    maths_marks NUMERIC(5,2),
    physics_marks NUMERIC(5,2),
    chemistry_marks NUMERIC(5,2),
    total_marks NUMERIC(6,2),
    percentage NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. ENQUIRIES TABLE
CREATE TABLE enquiries (
    enquiry_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id),
    full_name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    query_subject TEXT,
    query_description TEXT,
    status VARCHAR(50) DEFAULT 'open',
    assigned_to INTEGER REFERENCES users(user_id),
    response TEXT,
    responded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. ADMISSION_APPLICATIONS TABLE
CREATE TABLE admission_applications (
    app_id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id),
    registration_id VARCHAR(50) UNIQUE,
    academic_id INTEGER REFERENCES academic_details(academic_id),
    primary_dept_id INTEGER REFERENCES departments(dept_id),
    secondary_dept_id INTEGER REFERENCES departments(dept_id),
    cutoff_score NUMERIC(6,2),
    merit_rank INTEGER,
    application_status VARCHAR(50) DEFAULT 'step1',
    step1_completed BOOLEAN DEFAULT FALSE,
    step2_completed BOOLEAN DEFAULT FALSE,
    step3_completed BOOLEAN DEFAULT FALSE,
    admission_status VARCHAR(50) DEFAULT 'pending',
    allocated_dept_id INTEGER REFERENCES departments(dept_id),
    allocated_category VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. ADMISSION_HISTORY TABLE
CREATE TABLE admission_history (
    history_id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES admission_applications(app_id),
    status_before VARCHAR(50),
    status_after VARCHAR(50),
    changed_by INTEGER REFERENCES users(user_id),
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. AUDIT_LOG TABLE
CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    action VARCHAR(200),
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. SESSION_LOG TABLE
CREATE TABLE session_log (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    ip_address VARCHAR(50),
    user_agent TEXT
);

-- 12. DOCUMENTS TABLE
CREATE TABLE documents (
    doc_id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES admission_applications(app_id),
    document_type VARCHAR(100),
    document_url VARCHAR(500),
    file_size INTEGER,
    uploaded_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12A. ADMISSIONS TABLE (Branch Selection)
CREATE TABLE admissions (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL UNIQUE REFERENCES students(student_id) ON DELETE CASCADE,
    preferred_dept_id BIGINT NOT NULL REFERENCES departments(id),
    optional_dept_id TEXT,
    status VARCHAR(50) DEFAULT 'branch_selection_pending',
    allotted_dept_id BIGINT REFERENCES departments(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 13. NOTIFICATIONS TABLE
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    title VARCHAR(200),
    message TEXT,
    notification_type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. ADMISSION_REPORT TABLE (for daily reports)
CREATE TABLE admission_reports (
    report_id SERIAL PRIMARY KEY,
    report_date DATE DEFAULT CURRENT_DATE,
    dept_id INTEGER NOT NULL REFERENCES departments(dept_id),
    total_mq_seats INTEGER,
    total_gq_seats INTEGER,
    admitted_mq INTEGER DEFAULT 0,
    admitted_gq INTEGER DEFAULT 0,
    admitted_gq_special INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_users_employee_id ON users(employee_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_students_email ON students(email);
CREATE INDEX idx_students_registration_id ON students(registration_id);
CREATE INDEX idx_applications_student_id ON admission_applications(student_id);
CREATE INDEX idx_applications_status ON admission_applications(application_status);
CREATE INDEX idx_enquiries_student_id ON enquiries(student_id);
CREATE INDEX idx_enquiries_status ON enquiries(status);
CREATE INDEX idx_academic_details_student_id ON academic_details(student_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_session_log_user_id ON session_log(user_id);
CREATE INDEX idx_admission_reports_date ON admission_reports(report_date);

-- ============================================
-- DEFAULT SUPER ADMIN USER (CHANGE PASSWORD!)
-- ============================================
-- Username: super_admin@pmc.edu
-- Password: admin123 (CHANGE THIS IMMEDIATELY)

INSERT INTO users (employee_id, email, password, first_name, last_name, role_id, is_active)
VALUES ('EMP00001', 'super_admin@pmc.edu', 'admin123', 'System', 'Administrator', 1, TRUE);
