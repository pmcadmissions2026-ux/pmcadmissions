# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Script to diagnose which tables exist and what data they contain
for student PMC25000126 (SANJAYA KUMAY K)
"""

from database.supabase_config import db
import sys
import json

def check_student_data(student_id):
    """Check what data exists for a student"""
    
    print("\n" + "="*80)
    print("CHECKING DATA FOR STUDENT: " + str(student_id))
    print("="*80 + "\n")
    
    # Try to find student by unique_id first
    try:
        students_by_id = db.select('students', filters={'unique_id': student_id})
        if students_by_id:
            student = students_by_id[0]
            print("[OK] Found student in 'students' table")
            print("   Student ID: " + str(student.get('id')))
            print("   Name: " + str(student.get('full_name') or student.get('name')))
            sid = student.get('id')
        else:
            print("[ERROR] Student not found by unique_id: " + str(student_id))
            return
    except Exception as e:
        print("[ERROR] Error searching students table: " + str(e))
        return
    
    # Now check all related tables
    tables_to_check = {
        'academics': 'Academic Details',
        'academic_details': 'Academic Details (alt)',
        'enquiries': 'Enquiries',
        'admissions': 'Admissions',
        'admission_applications': 'Admission Applications',
        'documents': 'Documents',
        'counselling_records': 'Counselling Records',
        'payments': 'Payments'
    }
    
    for table_name, label in tables_to_check.items():
        try:
            records = db.select(table_name, filters={'student_id': sid})
            if records:
                print("\n[OK] " + label + " (Table: " + table_name + ")")
                print("   Count: " + str(len(records)))
                if records:
                    first_record = records[0]
                    print("   Columns: " + str(list(first_record.keys())))
                    data_str = json.dumps(first_record, indent=6, default=str)[:500]
                    print("   Data: " + data_str + "...")
            else:
                print("\n[MISSING] " + label + " (Table: " + table_name + ") - NO RECORDS")
        except Exception as e:
            print("\n[ERROR] " + label + " (Table: " + table_name + ") - ERROR: " + str(e))
    
    # Also check if student has enquiry reference
    print("\n" + "="*80)
    print("STUDENT RECORD DETAILS")
    print("="*80)
    
    try:
        students = db.select('students', filters={'id': sid})
        if students:
            student = students[0]
            print("\nAll fields in 'students' table:")
            for key, value in student.items():
                print("  " + str(key) + ": " + str(value))
    except Exception as e:
        print("Error fetching student details: " + str(e))

if __name__ == '__main__':
    # Use command line argument or default
    student_id = sys.argv[1] if len(sys.argv) > 1 else 'PMC25000126'
    check_student_data(student_id)
