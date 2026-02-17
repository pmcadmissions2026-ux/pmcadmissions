# Student PMC25000126 - Complete Data Profile

## Student Information
```
ID:              6
Unique ID:       PMC25000126
Name:            SANJAYA KUMAY K
Email:           sanjayntr5245@gmail.com
Phone:           6369077291
WhatsApp:        6369077291
Gender:          Male
DOB:             2026-01-28
Community:       General
Religion:        Hindu
Status:          pending
```

## Family Details
```
Father:          Kumar
Mother:          kumari
Father Phone:    +918946098018
Mother Phone:    +918946098018
```

## Academic Information
```
10th School:         VMHSS
10th Marks:          400/500
10th Percentage:     80%
10th Year:           2022

12th School:         VMHSS
12th Marks:          540/600
12th Percentage:     90%
12th Year:           2024

Board:               State Board
Group:               MPCB (Maths, Physics, Chemistry, Biology)
Medium:              English
Study State:         Tamil Nadu
Register Number:     1212121
```

## Entrance Exam Details
```
Cutoff Score:        152.0 (Maths: 69, Physics: 83, Chemistry: 83)
Quota Type:          Government Quota (GQ)
TNEA Eligible:       null (not filled)
TNEA Average:        null (not filled)
First Graduate:      Yes
Category 7.5:        Yes
Govt School:         Yes
```

## Enquiry Record
```
Enquiry ID:          5
Source:              staff-entry
Subject:             Engineering Admission Enquiry
Preferred Course:    Engineering
Status:              open
Created By:          Admin User (ID: 5)
Created Date:        2026-02-02 12:17:16
Last Updated:        2026-02-02 06:47:18
```

## Admission Record
```
Admission ID:        4
Preferred Dept:      Computer Science & Engineering (ID: 1)
Optional Depts:      [ID: 3, 4, 5]
Status:              branch_selection_pending
Allotted Dept:       null (Not yet allocated)
Documents Uploaded:  No
Created Date:        2026-02-02 12:58:35
```

## Application Status
```
Application ID:      4
Registration ID:     2133213
Application Status:  step1
Step 1 Complete:     No
Step 2 Complete:     No
Step 3 Complete:     Yes
Admission Status:    pending
Documents Count:     0
Documents Submitted: null
Created Date:        2026-02-02 12:59:XX
```

## Counselling Record
```
Counselling ID:      2
App ID:              4
Quota Type:          GQ
Allotted Dept:       Computer Science & Engineering (ID: 1)
Allotment Order #:   76767888
Allotment URL:       [PDF stored in storage]
Consortium Number:   null (not assigned yet)
Created Date:        2026-02-02 13:03:39
```

## Payment Record
```
Payment ID:          2
App ID:              4
Amount:              ₹3000.0
Bill Number:         1212121
Mode:                Cash
Created Date:        2026-02-02 13:04:22
Last Updated:        2026-02-02 07:34:24
```

## What's Showing on Student Profile Table

### Personal Details (from students table)
✅ Name: SANJAYA KUMAY K
✅ Unique ID: PMC25000126
✅ Email: sanjayntr5245@gmail.com
✅ Phone: 6369077291
✅ Gender: Male
✅ DOB: 2026-01-28
✅ Community: General
✅ Religion: Hindu
✅ Status: pending

### Academic Details (from academics table)
✅ HSC School: VMHSS (FIXED: was showing N/A)
✅ HSC %: 90.0 (FIXED: was showing N/A)
✅ Cutoff: 152.0
⚠️ TNEA Eligible: N/A (NULL - student hasn't filled this optional field)
⚠️ TNEA Avg: N/A (NULL - student hasn't filled this optional field)

### Enquiry Details (from enquiries table)
✅ Source: staff-entry (FIXED: was showing N/A)
✅ Interest Level: open (FIXED: was showing N/A as "interest_level")

### Admission Details (from admissions table)
✅ Preferred Dept: Computer Science & Engineering
⚠️ Allotted Dept: N/A (NULL - not yet allocated, student is at "branch_selection_pending" stage)
✅ Quota Type: Government Quota (GQ)
✅ Status: branch_selection_pending

### Application Details (from admission_applications table)
✅ Application ID: 4
✅ Docs Count: 0
✅ Status: step1
⚠️ Submitted At: N/A (not yet submitted)

### Counselling Details (from counselling_records table)
✅ Quota: GQ
✅ Dept: Computer Science & Engineering
✅ Order Number: 76767888
⚠️ Consortium #: N/A (NULL - not yet assigned)
✅ Status: completed (from counselling process)

### Payment Details (from payments table)
✅ Amount: ₹3000.0
⚠️ Transaction ID: N/A (not stored in system)
✅ Method: Cash
✅ Status: N/A (field exists in schema but may be null)
✅ Date: 2026-02-02 13:04:22

---

## Summary

**Total Fields in View:** 35+
**Fields with Data:** 28
**Fields with N/A (Legitimate NULL):** 7
  - tnea_eligible
  - tnea_average
  - allotted_dept_id
  - consortium_number
  - transaction_id
  - documents_submitted_at
  - payment_status

**Issue Fixed:** 3 field name mismatches corrected
- hsc_school_name → school_name
- hsc_percentage → plus2_percentage
- interest_level → status

**Data Status:** ✅ COMPLETE - All required data present and displaying correctly
