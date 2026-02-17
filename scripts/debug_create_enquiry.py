import sys, os
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from database.models import EnquiryModel

print('Creating enquiry via EnquiryModel.create_enquiry...')
try:
    res = EnquiryModel.create_enquiry('Local Test', '9999999999', 'localtest@example.com', 'Query Subject', 'This is a test enquiry')
    print('Result:', res)
except Exception as e:
    import traceback
    print('Exception:', e)
    traceback.print_exc()
