import os
import sys
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from database.models import EnquiryModel

# Call EnquiryModel.create_enquiry with positional args matching the signature
student_id = None
student_name = 'SDK Test User'
whatsapp_number = '9876543210'
email = 'sdk.test@example.com'
subject = 'SDK Insert Test'
preferred_course = 'Undeclared'
source = 'sdk-script'
created_by = None

print('Calling EnquiryModel.create_enquiry(...)')
try:
    res = EnquiryModel.create_enquiry(student_id, student_name, whatsapp_number, email, subject, preferred_course, source, created_by)
    print('result:', res)
except Exception as e:
    print('exception:', repr(e))
