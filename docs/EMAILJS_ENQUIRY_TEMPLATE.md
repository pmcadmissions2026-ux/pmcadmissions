
Subject: Enquiry Received - {{unique_id}}

Hello {{student_name}},

Greetings from Er. Perumal Manimekalai College of Engineering.

Thank you for contacting us. We have received your enquiry with the details below:

Student Unique ID: {{unique_id}}
Subject: {{subject}}
Message:
{{description}}

Our admissions team will review your query and get back to you shortly.

Best regards,
Er. Perumal Manimekalai College of Engineering
Admissions Office

---

Instructions:
1. Create a new template in EmailJS (Dashboard → Email Templates).
2. Use the above Subject and Body.
3. Note the `template_id` EmailJS assigns (example: `template_2yyrt7d`) and set it in your .env as `EMAILJS_TEMPLATE_ID` if you don't want to use the built-in default.
4. Add your EmailJS public key to `.env` as `EMAILJS_PUBLIC_KEY`.
5. The Flask app already has `EMAILJS_SERVICE_ID` defaulted to `service_j9uyccf` or override in `.env` as `EMAILJS_SERVICE_ID`.

Template variables available (use in template):
- `student_name`
- `unique_id`  (the student's unique ID stored in the `students` table; will be 'N/A' if not found)
- `subject`
- `description`
- `college_name`
