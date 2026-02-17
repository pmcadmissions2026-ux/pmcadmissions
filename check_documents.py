from supabase import create_client
import json

# Initialize Supabase client
url = "https://aoxdsfabgqrtdqjlwtow.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFveGRzZmFiZ3FydGRxamx3dG93Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzMwNDcwNzIsImV4cCI6MjA0ODYyMzA3Mn0.XYiVRFiATEXVU8H6HlPHKLe6LPB5-kI1bG-2H5BkU-A"
client = create_client(url, key)

# Get student ID 526 (PMC25000526)
student = client.table('students').select('*').eq('id', 526).execute()
print("Student:", student.data)

# Get applications for this student
apps = client.table('admission_applications').select('*').eq('student_id', 526).execute()
print("\nApplications:")
for app in apps.data:
    print(f"  App ID {app['id']}: {app}")

# Get documents for app_id 7
docs = client.table('documents').select('*').eq('application_id', 7).execute()
print(f"\nDocuments for application_id 7:")
print(json.dumps(docs.data, indent=2))
