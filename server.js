const path = require('path');
require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const morgan = require('morgan');
const cookieSession = require('cookie-session');
const { createClient } = require('@supabase/supabase-js');
const multer = require('multer');
const uploadMemory = multer({ storage: multer.memoryStorage() });

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
if(!SUPABASE_URL || !SUPABASE_SERVICE_KEY){
  console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment');
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Helper: generate unique student id with 'PMC' prefix and year-based sequence, e.g. PMC25000326
async function generateUniqueStudentId(){
  try{
    const yy = new Date().getFullYear().toString().slice(-2); // '25'
    // fetch recent students that look like they have our prefix or numeric start
    const { data: rows, error } = await supabase.from('students').select('unique_id').ilike('unique_id', `%${yy}%`).order('id', { ascending: false }).limit(500);
    if(error) {
      console.warn('generateUniqueStudentId lookup error', error.message);
    }
    let maxSeq = 0;
    if(Array.isArray(rows)){
      for(const r of rows){
        if(!r || !r.unique_id) continue;
        // remove non-digits and look for a sequence that starts with yy
        const digits = (r.unique_id.match(/(\d+)/) || [])[0];
        if(!digits) continue;
        if(digits.startsWith(yy)){
          const seq = parseInt(digits.slice(yy.length), 10);
          if(!isNaN(seq) && seq > maxSeq) maxSeq = seq;
        }
        // also support values like PMC25xxxx where digits may follow after prefix
        const m = r.unique_id.match(/PMC(\d{2})(\d+)/);
        if(m){ const seq2 = parseInt(m[2],10); if(!isNaN(seq2) && seq2 > maxSeq) maxSeq = seq2; }
      }
    }
    const next = maxSeq + 1;
    const padded = String(next).padStart(6, '0');
    return `PMC${yy}${padded}`;
  }catch(e){ console.warn('generateUniqueStudentId error', e); const yy = new Date().getFullYear().toString().slice(-2); return `PMC${yy}` + String(Date.now()).slice(-6); }
}

const app = express();
app.use(morgan('dev'));
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use(cookieSession({
  name: 'pmc_session',
  keys: [process.env.SESSION_SECRET || process.env.SECRET_KEY || 'replace-this'],
  maxAge: 24 * 60 * 60 * 1000 // 1 day
}));

// Serve your existing static assets and templates directories
app.use('/static', express.static(path.join(__dirname, 'static')));
app.use('/templates', express.static(path.join(__dirname, 'templates')));

// Simple route mapping to static HTML templates - adapt paths as needed
// Serve root login - use auth/login.html if present
app.get('/', (req, res) => {
  const candidate = path.join(__dirname, 'templates', 'auth', 'login.html');
  if(require('fs').existsSync(candidate)) return res.sendFile(candidate);
  return res.status(404).send('Login page not found');
});

// Counselling records endpoints
// GET /api/counselling_records?app_id=123  - list or filter
app.get('/api/counselling_records', async (req, res) => {
  try{
    const appId = req.query.app_id || req.query.appid;
    let query = supabase.from('counselling_records').select('*').order('created_at', { ascending: false }).limit(500);
    if(appId) query = supabase.from('counselling_records').select('*').eq('app_id', Number(appId)).order('created_at', { ascending: false }).limit(50);
    const { data, error } = await query;
    if(error) return res.status(500).json({ ok: false, error: error.message });
    return res.json(Array.isArray(data) ? data : (data && data.items ? data.items : []));
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// POST /api/counselling_records - create or update counselling record
app.post('/api/counselling_records', uploadMemory.any(), async (req, res) => {
  try{
    // accept both application/json and multipart/form-data
    const files = req.files || [];
    const body = req.body || {};
    const app_id = body.app_id || body.appId || null;
    if(!app_id) return res.status(400).json({ ok:false, error: 'app_id is required' });

    // find admission_applications row to get student_id
    const { data: appRow, error: appErr } = await supabase.from('admission_applications').select('app_id,student_id').eq('app_id', Number(app_id)).maybeSingle();
    if(appErr) return res.status(500).json({ ok:false, error: appErr.message });
    if(!appRow || !appRow.app_id) return res.status(404).json({ ok:false, error: `admission_applications not found for app_id ${app_id}` });
    const student_id = appRow.student_id;

    // build record object
    const record = {
      app_id: Number(app_id),
      student_id: student_id || null,
      quota_type: body.quota_type || (body.applied_gq ? 'GQ' : (body.applied_mq ? 'MQ' : (body.quota_type || null))) || null,
      allotted_dept_id: body.allotted_dept_id ? Number(body.allotted_dept_id) : (body.allotted_dept_id === '' ? null : null),
      allotment_order_number: body.allotment_order_number || null,
      consortium_number: body.consortium_number || null,
      applied_gq: body.applied_gq === 'true' || body.applied_gq === true || body.applied_gq === '1' || false,
      gq_application_number: body.gq_application_number || null,
      gq_applied_at: body.gq_applied_at || null,
      applied_mq: body.applied_mq === 'true' || body.applied_mq === true || body.applied_mq === '1' || false,
      mq_consortium_number: body.mq_consortium_number || null,
      mq_applied_at: body.mq_applied_at || null
    };

    // if file uploaded (allotment_order_pdf), upload to storage and set URL
    if(files && files.length > 0){
      const f = files.find(x => x.fieldname === 'allotment_order_pdf') || files[0];
      if(f){
        const remotePath = `counselling/${String(app_id)}/${Date.now()}_${f.originalname}`;
        const { data: upData, error: upErr } = await supabase.storage.from('Student_files').upload(remotePath, f.buffer, { contentType: f.mimetype, upsert: false });
        if(upErr) console.warn('upload allotment_order_pdf error', upErr.message);
        else {
          const publicUrl = `${SUPABASE_URL.replace(/\/$/,'')}/storage/v1/object/public/Student_files/${encodeURIComponent(upData.path)}`;
          record.allotment_order_url = publicUrl;
        }
      }
    }

    // Upsert: check existing record for app_id
    const { data: existing, error: existingErr } = await supabase.from('counselling_records').select('*').eq('app_id', Number(app_id)).maybeSingle();
    if(existingErr) console.warn('lookup counselling_records error', existingErr.message);
    // If inserting a new record and allotted_dept_id is missing, supply a fallback department id
    // to satisfy the DB NOT NULL / FK constraint. Frontend will still treat records without
    // allotment identifiers as 'Applied' (not Completed).
    if(!existing || !existing.counselling_id){
      if(!record.allotted_dept_id){
        const { data: depts, error: deptErr } = await supabase.from('departments').select('id').order('id', { ascending: true }).limit(1);
        if(deptErr) console.warn('departments lookup error', deptErr.message);
        if(Array.isArray(depts) && depts.length > 0){
          record.allotted_dept_id = depts[0].id;
          console.log('counselling_records: using fallback allotted_dept_id', record.allotted_dept_id);
        } else {
          return res.status(400).json({ ok:false, error: 'no departments configured; please create a department before saving counselling records' });
        }
      }
    }

    if(existing && existing.counselling_id){
      // update
      const { data: updated, error: updErr } = await supabase.from('counselling_records').update(record).eq('counselling_id', existing.counselling_id).select().maybeSingle();
      if(updErr) return res.status(500).json({ ok:false, error: updErr.message });
      return res.json({ ok: true, record: updated });
    } else {
      // insert
      const { data: inserted, error: insErr } = await supabase.from('counselling_records').insert(record).select().maybeSingle();
      if(insErr) return res.status(500).json({ ok:false, error: insErr.message });
      return res.json({ ok: true, record: inserted });
    }
  }catch(e){ console.error('counselling_records POST error', e); return res.status(500).json({ ok:false, error: String(e) }); }
});
app.get('/admin/admin-branch-management', (req, res) => res.sendFile(path.join(__dirname, 'templates', 'admin', 'admin-branch-management.html')));
// Serve admin dashboards
app.get('/admin/admin_dashboard', (req, res) => {
  const p = path.join(__dirname, 'templates', 'admin', 'admin_dashboard.html');
  if(require('fs').existsSync(p)) return res.sendFile(p);
  return res.status(404).send('admin_dashboard not found');
});

app.get('/admin/super_admin_dashboard', (req, res) => {
  const p = path.join(__dirname, 'templates', 'admin', 'super_admin_dashboard.html');
  if(require('fs').existsSync(p)) return res.sendFile(p);
  return res.status(404).send('super_admin_dashboard not found');
});

// Serve a small client config JS so frontend can access safe env (anon) values
app.get('/config.js', (req, res) => {
  const clientConfig = {
    SUPABASE_URL: process.env.SUPABASE_URL || null,
    SUPABASE_KEY: process.env.SUPABASE_KEY || null
  };
  res.type('application/javascript').send(`window.__ENV = ${JSON.stringify(clientConfig)};`);
});
// --- API: basic student/admission endpoints using Supabase service key ---
app.get('/api/students', async (req, res) => {
  try{
    const { data, error } = await supabase.from('students').select('*').limit(500);
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

app.get('/api/enquiries', async (req, res) => {
  try{
    const { data: enquiries, error } = await supabase.from('enquiries').select('*').order('created_at', { ascending: false }).limit(500);
    if(error) return res.status(500).json({ error: error.message });

    // Collect student_ids to fetch academics (cutoff, tnea_eligible)
    const studentIds = Array.from(new Set(enquiries.filter(e => e.student_id).map(e => e.student_id)));
    let academicsMap = {};
    if(studentIds.length > 0){
      const { data: academics, error: acadErr } = await supabase.from('academics').select('student_id,cutoff,tnea_eligible').in('student_id', studentIds);
      if(!acadErr && Array.isArray(academics)){
        academics.forEach(a => { if(a && a.student_id) academicsMap[String(a.student_id)] = a; });
      }
    }

    // Attach academic info to each enquiry
    const merged = enquiries.map(enq => {
      const acad = enq.student_id ? academicsMap[String(enq.student_id)] : null;
      return Object.assign({}, enq, { cutoff: acad && (acad.cutoff !== undefined) ? acad.cutoff : null, tnea_eligible: acad && (acad.tnea_eligible !== undefined) ? acad.tnea_eligible : null });
    });

    res.json(merged);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Create student + academics + enquiry in sequence
app.post('/api/enquiries', async (req, res) => {
  try{
    const { student, academic, enquiry } = req.body || {};
    if(!student || !student.full_name){
      return res.status(400).json({ error: 'student.full_name is required' });
    }

    // Insert student
    // ensure unique_id exists
    if(!student.unique_id){
      student.unique_id = await generateUniqueStudentId();
    }
    const { data: createdStudent, error: studentErr } = await supabase.from('students').insert(student).select().maybeSingle();
    if(studentErr) return res.status(500).json({ error: studentErr.message });

    const studentId = createdStudent && createdStudent.id;

    // Insert academics if provided
    let createdAcademic = null;
    if(academic){
      academic.student_id = studentId;
      const { data: acadData, error: acadErr } = await supabase.from('academics').insert(academic).select().maybeSingle();
      if(acadErr) return res.status(500).json({ error: acadErr.message });
      createdAcademic = acadData;
    }

    // Insert enquiry
    const enquiryRow = Object.assign({}, enquiry || {}, { student_id: studentId, student_name: student.full_name, whatsapp_number: student.whatsapp_number || student.phone || null });
    const { data: createdEnquiry, error: enquiryErr } = await supabase.from('enquiries').insert(enquiryRow).select().maybeSingle();
    if(enquiryErr) return res.status(500).json({ error: enquiryErr.message });

    res.json({ ok: true, student: createdStudent, academic: createdAcademic, enquiry: createdEnquiry });
  }catch(e){
    console.error('create enquiry error', e);
    res.status(500).json({ error: String(e) });
  }
});

app.get('/api/admissions', async (req, res) => {
  try{
    const { data, error } = await supabase.from('admissions').select('*').limit(500);
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Departments list
app.get('/api/departments', async (req, res) => {
  try{
    const { data, error } = await supabase.from('departments').select('*').order('dept_name', { ascending: true }).limit(1000);
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Student endpoints
app.get('/api/students/:id', async (req, res) => {
  try{
    const id = req.params.id;
    const { data, error } = await supabase.from('students').select('*').eq('id', id).maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

app.post('/api/students', async (req, res) => {
  try{
    const student = req.body;
    if(!student || !student.full_name) return res.status(400).json({ error: 'full_name required' });
    if(!student.unique_id){
      student.unique_id = await generateUniqueStudentId();
    }
    const { data, error } = await supabase.from('students').insert(student).select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Accept student (mark accepted)
app.post('/api/students/:id/accept', async (req, res) => {
  try{
    const id = req.params.id;
    const actor = req.body.accepted_by || (req.session && req.session.user && req.session.user.name) || null;
    const { data, error } = await supabase.from('students').update({ status: 'accepted', accepted_by: actor, accepted_at: new Date().toISOString() }).eq('id', id).select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Create admission record
app.post('/api/admissions', async (req, res) => {
  try{
    const { student_id, preferred_dept_id, optional_dept_ids } = req.body || {};
    if(!student_id || !preferred_dept_id) return res.status(400).json({ error: 'student_id and preferred_dept_id are required' });
    const row = { student_id, preferred_dept_id, optional_dept_ids: optional_dept_ids || [] };
    const { data, error } = await supabase.from('admissions').insert(row).select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Assign a branch to an admission (admin required)
app.post('/api/admissions/:id/assign', async (req, res) => {
  try{
    const id = req.params.id;
    const { allotted_dept_id, processed_by } = req.body;
    if(!allotted_dept_id) return res.status(400).json({ error: 'allotted_dept_id required' });
    const update = { allotted_dept_id, status: 'assigned', processed_by, processed_at: new Date().toISOString() };
    const { data, error } = await supabase.from('admissions').update(update).eq('id', id).select();
    if(error) return res.status(500).json({ error: error.message });
    res.json({ ok: true, updated: data });
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Documents metadata insert (used after client uploads to Supabase storage)
app.post('/api/documents', async (req, res) => {
  try{
    const { app_id, unique_id, student_unique, document_type, document_url, file_size, uploaded_by } = req.body || {};
    console.log('/api/documents payload', { app_id, unique_id, student_unique, document_type, document_url, file_size, uploaded_by });

    if(!document_url) return res.status(400).json({ error: 'document_url required' });

    let normalizedAppId = null;

    // If unique_id or student_unique provided, prefer mapping student -> admission_applications.app_id
      // If app_id is provided, prefer using it; otherwise use unique_id/student_unique to map
      const uidToUse = (!app_id) ? (unique_id || student_unique) : null;
    const debugInfo = {};
    if(uidToUse){
      const { data: student, error: sErr } = await supabase.from('students').select('id').eq('unique_id', uidToUse).maybeSingle();
      debugInfo.student = student || null;
      debugInfo.student_error = sErr ? (sErr.message || String(sErr)) : null;
      if(sErr) console.warn('lookup student by unique_id error', sErr.message);
      if(!student || !student.id){ console.log('/api/documents debug (no student)', debugInfo); return res.status(400).json({ error: `No student found for unique_id ${uidToUse}`, debug: debugInfo }); }
      const { data: apps, error: aErr } = await supabase.from('admission_applications').select('app_id').eq('student_id', student.id).order('created_at', { ascending: false }).limit(1).maybeSingle();
      debugInfo.apps = apps || null;
      debugInfo.apps_error = aErr ? (aErr.message || String(aErr)) : null;
      if(aErr) console.warn('lookup admission_applications by student_id error', aErr.message);
      if(!apps || !apps.app_id){ console.log('/api/documents debug (no apps)', debugInfo); return res.status(400).json({ error: `No admission_applications found for student with unique_id ${uidToUse}`, debug: debugInfo }); }
      normalizedAppId = Number(apps.app_id);
    }

    // If the caller provided a student identifier in the body (student_unique/unique_id), try to populate debugInfo.student
    // even when app_id was provided so we can auto-create fallback admission_applications when necessary.
    if(!debugInfo.student){
      const bodyUid = (unique_id || student_unique) || null;
      if(bodyUid){
        const { data: s2, error: s2Err } = await supabase.from('students').select('id').eq('unique_id', bodyUid).maybeSingle();
        debugInfo.student = s2 || null;
        debugInfo.student_error = s2Err ? (s2Err.message || String(s2Err)) : debugInfo.student_error || null;
      }
    }

    // If still not resolved, try app_id provided. Use the provided app_id directly (caller may supply admission_applications.app_id)
    if(!normalizedAppId && app_id){
      const candidate = Number(app_id);
      debugInfo.provided_app_id = candidate;
      // Prefer to verify whether the provided app_id actually exists. If it doesn't and we have a student, auto-create a new admission_applications for that student.
      const { data: existingCheck, error: checkErr } = await supabase.from('admission_applications').select('app_id').eq('app_id', candidate).maybeSingle();
      if(!checkErr && existingCheck && existingCheck.app_id){
        normalizedAppId = Number(existingCheck.app_id);
        console.log('/api/documents using existing admission_applications.app_id', normalizedAppId);
      } else {
        // If we know the student id, create a new admission_applications and use its app_id
        if(debugInfo && debugInfo.student && debugInfo.student.id){
          try{
            const newAppRow = { student_id: debugInfo.student.id, status: 'created', processed_by: null, processed_at: null };
            const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            if(!createErr && createdApp && createdApp.app_id){ normalizedAppId = Number(createdApp.app_id); console.log('/api/documents created admission_applications fallback', normalizedAppId); }
            else { normalizedAppId = candidate; console.log('/api/documents provided app_id not found but could not create fallback, will try provided', candidate); }
          }catch(e){ console.warn('create admission_applications exception', e); normalizedAppId = candidate; }
        } else {
          // No student known: fall back to using provided candidate and rely on DB to enforce FK
          normalizedAppId = candidate;
          console.log('/api/documents using provided app_id without creation', normalizedAppId);
        }
      }
    }

    if(!normalizedAppId){ console.log('/api/documents debug (no normalizedAppId)', debugInfo); return res.status(400).json({ error: 'Could not determine admission_applications.app_id from provided app_id or unique_id', debug: debugInfo }); }

    const row = { app_id: Number(normalizedAppId), document_type: document_type || null, document_url, file_size: file_size ? Number(file_size) : null, uploaded_by: uploaded_by ? Number(uploaded_by) : null };
    let insertAttempt = 0;
    while(true){
      insertAttempt++;
      const { data, error } = await supabase.from('documents').insert(row).select().maybeSingle();
      if(!error){ return res.json({ ok: true, document: data }); }
      // If FK error and we have student info, attempt to create a minimal admission_applications record and retry once
      const msg = error && (error.message || String(error));
      console.error('insert document error', msg);
      if(insertAttempt === 1 && msg && msg.includes('violates foreign key') && debugInfo && debugInfo.student && debugInfo.student.id){
        try{
          console.log('/api/documents attempting to create admission_applications fallback for student', debugInfo.student.id);
          const newAppRow = { student_id: debugInfo.student.id, status: 'created', processed_by: null, processed_at: null };
          let createdApp = null;
          try{
            const r = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            createdApp = r && r.data ? r.data : null;
            const createErr = r && r.error ? r.error : null;
            if(createErr){
              const msgCreate = createErr.message || String(createErr);
              console.warn('failed to create admission_applications fallback', msgCreate);
              // if schema mismatch (missing columns), retry with minimal payload
              if(msgCreate && (msgCreate.includes('Could not find') || msgCreate.includes('does not exist') || msgCreate.includes('column') || msgCreate.includes('schema cache'))){
                try{
                  const alt = { student_id: debugInfo.student.id };
                  const r2 = await supabase.from('admission_applications').insert(alt).select().maybeSingle();
                  const createErr2 = r2 && r2.error ? r2.error : null;
                  if(createErr2){ console.warn('fallback minimal create also failed', createErr2.message || String(createErr2)); return res.status(500).json({ error: msg }); }
                  createdApp = r2 && r2.data ? r2.data : null;
                }catch(e){ console.warn('fallback minimal create exception', e); return res.status(500).json({ error: msg }); }
              } else {
                return res.status(500).json({ error: msg });
              }
            }
          }catch(e){ console.warn('create admission_applications exception', e); return res.status(500).json({ error: msg }); }
          if(createdApp && createdApp.app_id){ normalizedAppId = Number(createdApp.app_id); row.app_id = normalizedAppId; console.log('created admission_applications', normalizedAppId); continue; }
        }catch(e){ console.warn('create admission_applications exception', e); return res.status(500).json({ error: msg }); }
      }
      return res.status(500).json({ error: msg });
    }
  }catch(e){ console.error('insert document error', e); res.status(500).json({ error: String(e) }); }
});

// Server-side upload endpoint: accepts a single file and uploads to Supabase storage using service key
app.post('/api/upload-file', uploadMemory.any(), async (req, res) => {
  try{
    const files = req.files || [];
    const { app_id, unique_id, student_unique, document_type, student_name, uploaded_by } = req.body || {};
    console.log('/api/upload-file payload', { app_id, unique_id, student_unique, document_type, student_name, uploaded_by, files: files.map(f=>({ field: f.fieldname, originalname: f.originalname, size: f.size })) });
    if(!files || files.length === 0) return res.status(400).json({ error: 'one or more files are required' });

    // determine app_id if unique_id or student_unique provided
    let targetAppId = null;
    const uidToUse = unique_id || student_unique;
    if(uidToUse){
      const { data: student, error: sErr } = await supabase.from('students').select('id').eq('unique_id', uidToUse).maybeSingle();
      if(sErr) console.warn('lookup student by unique_id error', sErr.message);
      if(!student || !student.id){ console.log('/api/upload-file debug (no student)', { uidToUse }); return res.status(400).json({ error: `No student found for unique_id ${uidToUse}` }); }
      const { data: apps, error: aErr } = await supabase.from('admission_applications').select('app_id').eq('student_id', student.id).order('created_at', { ascending: false }).limit(1).maybeSingle();
      if(aErr) console.warn('lookup admission_applications by student_id error', aErr.message);
      if(!apps || !apps.app_id){ console.log('/api/upload-file debug (no apps)', { uidToUse, apps }); return res.status(400).json({ error: `No admission_applications found for student with unique_id ${uidToUse}` }); }
      targetAppId = Number(apps.app_id);
    }

    if(!targetAppId && app_id) {
      const candidate = Number(app_id);
      // verify existence
      const { data: existingCheck, error: checkErr } = await supabase.from('admission_applications').select('app_id').eq('app_id', candidate).maybeSingle();
      if(!checkErr && existingCheck && existingCheck.app_id){ targetAppId = Number(existingCheck.app_id); }
      else if(uidToUse){
        // if we know the student, create a fallback admission_applications
        const { data: s2, error: s2Err } = await supabase.from('students').select('id').eq('unique_id', uidToUse).maybeSingle();
        if(!s2Err && s2 && s2.id){
          try{
            const newAppRow = { student_id: s2.id, status: 'created', processed_by: null, processed_at: null };
            const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            if(!createErr && createdApp && createdApp.app_id){ targetAppId = Number(createdApp.app_id); console.log('/api/upload-file created admission_applications', targetAppId); }
          }catch(e){ console.warn('create admission_applications exception', e); }
        }
      } else {
        targetAppId = candidate;
      }
    }
    if(!targetAppId){ console.log('/api/upload-file debug (no targetAppId)', { app_id, uidToUse }); return res.status(400).json({ error: 'app_id or unique_id required' }); }

    // mapping from incoming field names to normalized document_type used in documents table
    const fieldToDocType = {
      'file_10th_mark': '10th_Mark_Sheet',
      'file_12th_mark': '12th_Mark_Sheet',
      'file_community': 'Community_Certificate',
      'file_photo': 'Passport_Photo',
      'file_tc': 'Transfer_Certificate',
      'file_fg': 'FG_Certificate',
      '10th_Mark_Sheet': '10th_Mark_Sheet',
      '12th_Mark_Sheet': '12th_Mark_Sheet',
      'Community_Certificate': 'Community_Certificate',
      'Passport_Photo': 'Passport_Photo',
      'Transfer_Certificate': 'Transfer_Certificate',
      'FG_Certificate': 'FG_Certificate'
    };

    const results = [];
    for(const file of files){
      const incomingField = file.fieldname;
      const docType = fieldToDocType[incomingField] || document_type || incomingField;
      const remotePath = `${String(targetAppId)}/${Date.now()}_${file.originalname}`;
      const { data: upData, error: upErr } = await supabase.storage.from('Student_files').upload(remotePath, file.buffer, { contentType: file.mimetype, upsert: false });
      if(upErr) return res.status(500).json({ error: upErr.message });

      // construct public url
      const publicUrl = `${SUPABASE_URL.replace(/\/$/,'')}/storage/v1/object/public/Student_files/${encodeURIComponent(upData.path)}`;

      // insert metadata into documents table
      const row = { app_id: Number(targetAppId), document_type: docType || null, document_url: publicUrl, file_size: file.size ? Number(file.size) : null, uploaded_by: uploaded_by ? Number(uploaded_by) : null };
      let insertAttempt = 0;
      while(true){
        insertAttempt++;
        const { data: docData, error: docErr } = await supabase.from('documents').insert(row).select().maybeSingle();
        if(!docErr){ results.push({ ok: true, document: docData, publicUrl }); break; }
        const msg = docErr && (docErr.message || String(docErr));
        console.error('insert document error', msg);
        // If FK error and we have a student id from earlier lookup, try to create admission_applications fallback then retry once
        if(insertAttempt === 1 && msg && msg.includes('violates foreign key')){
          // attempt to discover student id if not already present
          let fallbackStudentId = null;
          if(uidToUse){
            const { data: student, error: sErr } = await supabase.from('students').select('id').eq('unique_id', uidToUse).maybeSingle();
            if(!sErr && student && student.id) fallbackStudentId = student.id;
          }
          if(fallbackStudentId){
            try{
              const newAppRow = { student_id: fallbackStudentId, status: 'created', processed_by: null, processed_at: null };
              let createdApp = null;
              try{
                const r = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
                createdApp = r && r.data ? r.data : null;
                const createErr = r && r.error ? r.error : null;
                if(createErr){
                  const msgCreate = createErr.message || String(createErr);
                  console.warn('failed to create admission_applications fallback', msgCreate);
                  if(msgCreate && (msgCreate.includes('Could not find') || msgCreate.includes('does not exist') || msgCreate.includes('column') || msgCreate.includes('schema cache'))){
                    try{
                      const alt = { student_id: fallbackStudentId };
                      const r2 = await supabase.from('admission_applications').insert(alt).select().maybeSingle();
                      const createErr2 = r2 && r2.error ? r2.error : null;
                      if(createErr2){ console.warn('fallback minimal create also failed', createErr2.message || String(createErr2)); results.push({ ok: false, error: msg }); break; }
                      createdApp = r2 && r2.data ? r2.data : null;
                    }catch(e){ console.warn('fallback minimal create exception', e); results.push({ ok: false, error: msg }); break; }
                  } else {
                    results.push({ ok: false, error: msg }); break;
                  }
                }
              }catch(e){ console.warn('create admission_applications exception', e); results.push({ ok: false, error: msg }); break; }
              if(createdApp && createdApp.app_id){ targetAppId = Number(createdApp.app_id); row.app_id = targetAppId; console.log('created admission_applications', targetAppId); continue; }
            }catch(e){ console.warn('create admission_applications exception', e); results.push({ ok: false, error: msg }); break; }
          }
        }
        results.push({ ok: false, error: msg }); break;
      }
    }

    return res.json({ ok: true, results });
  }catch(e){ console.error('server upload error', e); return res.status(500).json({ error: String(e) }); }
});

// Graceful handler for accidental native POSTs to the static HTML path
app.post('/templates/admin/document_upload.html', (req, res) => {
  // The page is intended to be client-driven. Return 204 No Content to avoid 404 noise.
  return res.status(204).send();
});

// Temporary diagnostic endpoint: list objects in the Student_files bucket
app.get('/api/_check_bucket', async (req, res) => {
  try{
    const bucketName = 'Student_files';
    const { data, error } = await supabase.storage.from(bucketName).list('', { limit: 50 });
    if(error) return res.status(500).json({ ok: false, error: error.message });
    return res.json({ ok: true, items: data });
  }catch(e){
    return res.status(500).json({ ok: false, error: String(e) });
  }
});

// Diagnostic: list documents rows (top 50)
app.get('/api/_documents', async (req, res) => {
  try{
    const { data, error } = await supabase.from('documents').select('*').limit(50);
    if(error) return res.status(500).json({ ok: false, error: error.message });
    return res.json({ ok: true, items: data });
  }catch(e){ return res.status(500).json({ ok: false, error: String(e) }); }
});

// Diagnostic: list counselling_records (top 500) - tolerant listing for admin UI
app.get('/api/_counselling_records', async (req, res) => {
  try{
    const { data, error } = await supabase.from('counselling_records').select('*').order('created_at', { ascending: false }).limit(500);
    if(error) return res.status(500).json({ ok: false, error: error.message });
    return res.json(Array.isArray(data) ? data : (data && data.items ? data.items : []));
  }catch(e){ return res.status(500).json({ ok: false, error: String(e) }); }
});

// Delete a document row and its storage object (if possible)
app.delete('/api/documents/:id', async (req, res) => {
  try{
    const docIdParam = req.params.id;
    const idNum = Number(docIdParam);
    if(isNaN(idNum)) return res.status(400).json({ ok: false, error: 'invalid id' });

    // Try to find by doc_id first, then by id
    let { data: docRow, error: qErr } = await supabase.from('documents').select('*').eq('doc_id', idNum).maybeSingle();
    if(qErr) console.warn('lookup documents.doc_id error', qErr.message);
    if(!docRow){ const r2 = await supabase.from('documents').select('*').eq('id', idNum).maybeSingle(); docRow = r2 && r2.data ? r2.data : r2 && r2.error ? null : r2; }

    if(!docRow) return res.status(404).json({ ok: false, error: 'document not found' });

    // Attempt to remove object from storage if document_url contains Student_files path
    try{
      const url = docRow.document_url || docRow.file_url || '';
      const marker = '/Student_files/';
      const idx = url.indexOf(marker);
      if(idx !== -1){
        const objectPath = decodeURIComponent(url.slice(idx + marker.length));
        await supabase.storage.from('Student_files').remove([objectPath]);
      }
    }catch(e){ console.warn('warning: could not delete storage object', e); }

    // Delete DB row
    const { data: delData, error: delErr } = await supabase.from('documents').delete().eq('doc_id', idNum);
    if(delErr){
      // try deleting by generic id if doc_id delete failed
      const r2 = await supabase.from('documents').delete().eq('id', idNum);
      if(r2.error) return res.status(500).json({ ok: false, error: r2.error.message || String(r2.error) });
      return res.json({ ok: true });
    }
    return res.json({ ok: true });
  }catch(e){ console.error('delete document error', e); return res.status(500).json({ ok: false, error: String(e) }); }
});

// Diagnostic: list admission_applications if present
app.get('/api/_admission_applications', async (req, res) => {
  try{
    const { data, error } = await supabase.from('admission_applications').select('*').limit(50);
    if(error) return res.status(500).json({ ok: false, error: error.message });
    return res.json({ ok: true, items: data });
  }catch(e){ return res.status(500).json({ ok: false, error: String(e) }); }
});

// Public: fetch a single admission_application by app_id
app.get('/api/admission_applications', async (req, res) => {
  try{
    const appId = req.query.app_id || req.query.appid || req.query.app;
    if(!appId) return res.status(400).json({ ok:false, error: 'app_id query param required' });
    const { data, error } = await supabase.from('admission_applications').select('*').eq('app_id', Number(appId)).maybeSingle();
    if(error) return res.status(500).json({ ok:false, error: error.message });
    if(!data) return res.status(404).json({ ok:false, error: 'not found' });
    return res.json({ ok:true, item: data });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Users: list users
app.get('/api/users', async (req, res) => {
  try{
    const { data, error } = await supabase.from('users').select('*').order('created_at', { ascending: false }).limit(1000);
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json(Array.isArray(data) ? data : (data && data.items ? data.items : []));
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Users: delete user by user_id
app.delete('/api/users/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(!id) return res.status(400).json({ ok:false, error: 'invalid id' });
    const { data, error } = await supabase.from('users').delete().eq('user_id', id);
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Users: create user
app.post('/api/users', async (req, res) => {
  try{
    const body = req.body || {};
    const employee_id = (body.employee_id || body.emp_id || '').toString().trim();
    const email = (body.email || '').toString().trim();
    const password = (body.password || '').toString();
    const first_name = (body.first_name || '').toString().trim();
    const last_name = (body.last_name || '').toString().trim();
    const phone = (body.phone || null);
    const role_id = body.role_id ? Number(body.role_id) : (body.roleId ? Number(body.roleId) : 2);
    const is_active = (body.is_active === undefined) ? true : Boolean(body.is_active);
    let assigned_modules = body.assigned_modules || body.modules || [];
    if(typeof assigned_modules === 'string'){
      try{ assigned_modules = JSON.parse(assigned_modules); }catch(e){ assigned_modules = []; }
    }

    if(!employee_id || !email) return res.status(400).json({ ok:false, error: 'employee_id and email required' });

    const row = { employee_id, email, password: password || 'changeme', first_name, last_name, phone, role_id, is_active, assigned_modules };
    const { data, error } = await supabase.from('users').insert(row).select().maybeSingle();
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true, user: data });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Users: update user
app.put('/api/users/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(!id) return res.status(400).json({ ok:false, error: 'invalid id' });
    const body = req.body || {};
    const updates = {};
    ['employee_id','email','first_name','last_name','phone'].forEach(k=>{ if(body[k]!==undefined) updates[k]=body[k]; });
    if(body.role_id!==undefined) updates.role_id = Number(body.role_id);
    if(body.is_active!==undefined) updates.is_active = Boolean(body.is_active);
    if(body.password) updates.password = body.password;
    if(body.assigned_modules!==undefined){ let am = body.assigned_modules; if(typeof am==='string'){ try{ am = JSON.parse(am); }catch(e){ am = []; } } updates.assigned_modules = am; }

    const { data, error } = await supabase.from('users').update(updates).eq('user_id', id).select().maybeSingle();
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true, user: data });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Payments: list payments
app.get('/api/payments', async (req, res) => {
  try{
    const { data, error } = await supabase.from('payments').select('*').order('created_at', { ascending: false }).limit(500);
    if(error) return res.status(500).json({ ok:false, error: error.message });
    const rows = Array.isArray(data) ? data : (data && data.items ? data.items : []);

    // enrich payments with student name and unique id where possible
    const studentIds = Array.from(new Set(rows.map(r => r && r.student_id).filter(Boolean).map(Number)));
    let students = [];
    if(studentIds.length > 0){
      const { data: studs, error: studsErr } = await supabase.from('students').select('*').in('id', studentIds);
      if(studsErr) console.warn('students lookup for payments failed', studsErr);
      if(Array.isArray(studs)){
        students = studs.map(s => {
          const display_name = s.full_name || s.student_name || s.name || s.fullname || ((s.first_name||'') + (s.last_name ? ' ' + s.last_name : '')) || null;
          const uniq = s.unique_id || s.uniqueId || s.registration_id || s.registration_no || null;
          return Object.assign({}, s, { display_name, uniq_id: uniq });
        });
      }
    }
    const studentMap = {};
    students.forEach(s => { if(s && s.id) studentMap[String(s.id)] = s; });

    const out = rows.map(p => {
      const stu = p && p.student_id ? studentMap[String(p.student_id)] : null;
      return Object.assign({}, p, {
        student_name: stu ? (stu.display_name || stu.full_name || stu.student_name) : p.student_name || null,
        unique_id: stu ? (stu.uniq_id || stu.unique_id) : p.unique_id || null
      });
    });

    return res.json(out);
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Payment candidates: apps that appear in counselling_records OR documents but are not present in payments
app.get('/api/payment_candidates', async (req, res) => {
  try{
    // gather app_ids from counselling_records and documents and payments (step-by-step)
    const { data: cData, error: cErr } = await supabase.from('counselling_records').select('app_id');
    if(cErr) console.warn('counselling_records lookup error', cErr.message || String(cErr));
    const { data: dData, error: dErr } = await supabase.from('documents').select('app_id');
    if(dErr) console.warn('documents lookup error', dErr.message || String(dErr));
    const { data: pData, error: pErr } = await supabase.from('payments').select('app_id');
    if(pErr) console.warn('payments lookup error', pErr.message || String(pErr));

    const cApps = Array.isArray(cData) ? cData.map(r => r.app_id).filter(Boolean) : [];
    const dApps = Array.isArray(dData) ? dData.map(r => r.app_id).filter(Boolean) : [];
    const paidApps = Array.isArray(pData) ? pData.map(r => r.app_id).filter(Boolean) : [];

    const all = new Set([...cApps.map(String), ...dApps.map(String)]);
    // remove already paid
    (paidApps||[]).map(String).forEach(x => all.delete(x));

    const appIds = Array.from(all).map(x => Number(x)).filter(x => !isNaN(x));
    if(appIds.length === 0) return res.json([]);

    // fetch admission_applications rows (select all to avoid column name mismatches)
    const { data: apps, error: appsErr } = await supabase.from('admission_applications').select('*').in('app_id', appIds);
    if(appsErr) { console.error('admission_applications lookup error', appsErr); return res.status(500).json({ ok:false, error: appsErr.message || String(appsErr) }); }

    let studentIds = apps.filter(a=>a && a.student_id).map(a => a.student_id);
    // For apps missing student_id, try to recover from counselling_records which may contain student_id
    const appsMissingStudent = apps.filter(a => !(a && a.student_id)).map(a => a.app_id).filter(Boolean);
    if(appsMissingStudent.length > 0){
      try{
        const { data: crs, error: crErr } = await supabase.from('counselling_records').select('app_id,student_id').in('app_id', appsMissingStudent);
        if(crErr) console.warn('counselling_records lookup for missing student_ids failed', crErr.message || crErr);
        if(Array.isArray(crs)){
          crs.forEach(r => { if(r && r.student_id) studentIds.push(r.student_id); });
        }
      }catch(e){ console.warn('counselling_records extra lookup exception', e); }
    }

    // Also fetch counselling_records for allotment info (allotted_dept_id, quota_type) and map by app_id
    let counsellingMap = {};
    try{
      const { data: crAll, error: crAllErr } = await supabase.from('counselling_records').select('app_id,allotted_dept_id,quota_type').in('app_id', appIds);
      if(crAllErr) console.warn('counselling_records lookup for allotment info failed', crAllErr.message || crAllErr);
      if(Array.isArray(crAll)){
        crAll.forEach(r => { if(r && r.app_id) counsellingMap[String(r.app_id)] = r; });
      }
    }catch(e){ console.warn('counselling_records allotment lookup exception', e); }

    // Deduplicate studentIds
    studentIds = Array.from(new Set(studentIds.map(x => Number(x)).filter(x => !isNaN(x))));
    let students = [];
    if(studentIds.length > 0){
      // select all columns to be tolerant of differing schemas
      const { data: studs, error: studsErr } = await supabase.from('students').select('*').in('id', studentIds);
      if(studsErr){ console.warn('students lookup error', studsErr); }
      if(Array.isArray(studs)){
        // normalize student rows with safe fallbacks for display name and unique id
        students = studs.map(s => {
          const display_name = s.full_name || s.student_name || s.name || s.fullname || ((s.first_name||'') + (s.last_name ? ' ' + s.last_name : '')) || null;
          const uniq = s.unique_id || s.uniqueId || s.registration_id || s.registration_no || null;
          return Object.assign({}, s, { display_name, uniq_id: uniq });
        });
      }else{
        students = [];
      }
    }

    const studentMap = {};
    (students||[]).forEach(s => { if(s && s.id) studentMap[String(s.id)] = s; });

    const out = apps.map(a => {
      const stu = a && (a.student_id || a.student) ? studentMap[String(a.student_id)] : null;
      // use safe fallbacks for possible differing column names
      const registration_id = a.registration_id || a.reg_id || a.registration_no || null;
      // Prefer counselling_records allotment fields when available
      const cr = counsellingMap[String(a.app_id)];
      const preferred_dept_id = (cr && cr.allotted_dept_id) ? cr.allotted_dept_id : (a.preferred_dept_id || a.allotted_dept_id || a.preferred_branch_id || a.dept_id || null);
      const quota_type = (cr && cr.quota_type) ? cr.quota_type : (a.quota_type || a.quota || null);
      return {
        app_id: a.app_id,
        student_id: a.student_id || null,
        student_name: stu ? (stu.display_name || stu.full_name || stu.student_name || stu.name || null) : null,
        unique_id: stu ? (stu.uniq_id || stu.unique_id || null) : null,
        registration_id: registration_id,
        preferred_dept_id: preferred_dept_id,
        quota_type: quota_type
      };
    });

    return res.json(out);
  }catch(e){ console.error('payment_candidates error', e && e.stack ? e.stack : e); return res.status(500).json({ ok:false, error: String(e) }); }
});

// Create a payment record
app.post('/api/payments', async (req, res) => {
  try{
    const body = req.body || {};
    const app_id = body.app_id || body.appId;
    const bill_no = body.bill_no || body.billNo || null;
    const mode_of_payment = body.mode_of_payment || body.mode || null;
    const amount = (body.amount !== undefined && body.amount !== null) ? Number(body.amount) : null;
    const upi_id = body.upi_id || body.upiId || null;

    if(!app_id) return res.status(400).json({ ok:false, error: 'app_id is required' });
    if(!bill_no) return res.status(400).json({ ok:false, error: 'bill_no is required' });
    if(!mode_of_payment) return res.status(400).json({ ok:false, error: 'mode_of_payment is required' });
    if(amount === null || isNaN(amount)) return res.status(400).json({ ok:false, error: 'amount is required and must be numeric' });

    // find admission_applications to obtain student_id
    const { data: appRow, error: appErr } = await supabase.from('admission_applications').select('app_id,student_id').eq('app_id', Number(app_id)).maybeSingle();
    if(appErr) return res.status(500).json({ ok:false, error: appErr.message });
    if(!appRow || !appRow.app_id) return res.status(404).json({ ok:false, error: `admission_applications not found for app_id ${app_id}` });
    const student_id = appRow.student_id;
    if(!student_id) return res.status(400).json({ ok:false, error: 'cannot determine student_id for this app_id' });

    const row = { app_id: Number(app_id), student_id: Number(student_id), bill_no: String(bill_no), mode_of_payment: String(mode_of_payment), amount: Number(amount) };
    if(upi_id) row.upi_id = String(upi_id);

    const { data: inserted, error: insErr } = await supabase.from('payments').insert(row).select().maybeSingle();
    if(insErr) return res.status(500).json({ ok:false, error: insErr.message });
    return res.json({ ok:true, payment: inserted });
  }catch(e){ console.error('create payment error', e); return res.status(500).json({ ok:false, error: String(e) }); }
});

// Public: fetch documents by admission app_id
app.get('/api/documents', async (req, res) => {
  try{
    const appId = req.query.app_id || req.query.appid || req.query.app;
    const uniqueId = req.query.unique_id || req.query.unique;
    let targetAppIds = [];
    if(uniqueId){
      // find student by unique_id
      const { data: student, error: sErr } = await supabase.from('students').select('id').eq('unique_id', uniqueId).maybeSingle();
      if(sErr) return res.status(500).json({ error: sErr.message });
      if(!student || !student.id) return res.status(404).json({ error: `No student found for unique_id ${uniqueId}` });
      // find admission_applications for this student
      const { data: apps, error: aErr } = await supabase.from('admission_applications').select('app_id').eq('student_id', student.id);
      if(aErr) return res.status(500).json({ error: aErr.message });
      if(!Array.isArray(apps) || apps.length === 0) return res.status(404).json({ error: `No admission_applications found for student id ${student.id}` });
      targetAppIds = apps.map(x => x.app_id).filter(x => x !== null && x !== undefined);
    } else if(appId){
      targetAppIds = [Number(appId)];
    } else {
      return res.status(400).json({ error: 'app_id or unique_id query parameter required' });
    }

    const { data, error } = await supabase.from('documents').select('*').in('app_id', targetAppIds).order('created_at', { ascending: false }).limit(500);
    if(error) return res.status(500).json({ error: error.message });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Return document counts keyed by student unique_id (accepts comma-separated unique_ids)
app.get('/api/documents/counts', async (req, res) => {
  try{
    const uniqs = req.query.unique_ids || req.query.uniqueIds || req.query.uids;
    if(!uniqs) return res.status(400).json({ error: 'unique_ids query parameter required (comma separated)' });
    const uniqueList = uniqs.split(',').map(s => s.trim()).filter(Boolean);
    if(uniqueList.length === 0) return res.status(400).json({ error: 'no unique_ids provided' });

    // find students
    const { data: students, error: sErr } = await supabase.from('students').select('id,unique_id').in('unique_id', uniqueList);
    if(sErr) return res.status(500).json({ error: sErr.message });
    const studentIdMap = {}; // student_id -> unique_id
    const studentIds = [];
    (students||[]).forEach(s => { studentIdMap[s.id] = s.unique_id; studentIds.push(s.id); });

    if(studentIds.length === 0){
      // return zeros for all requested
      const out = {};
      uniqueList.forEach(u => out[u] = 0);
      return res.json(out);
    }

    // find admission_applications for these students
    const { data: apps, error: aErr } = await supabase.from('admission_applications').select('app_id,student_id').in('student_id', studentIds);
    if(aErr) return res.status(500).json({ error: aErr.message });
    const appIds = (apps||[]).map(x => x.app_id).filter(x => x !== null && x !== undefined);

    if(appIds.length === 0){
      const out = {};
      uniqueList.forEach(u => out[u] = 0);
      return res.json(out);
    }

    // fetch documents for these app_ids
    const { data: docs, error: dErr } = await supabase.from('documents').select('app_id').in('app_id', appIds);
    if(dErr) return res.status(500).json({ error: dErr.message });

    // count per app_id
    const countsByApp = {};
    (docs||[]).forEach(d => { countsByApp[d.app_id] = (countsByApp[d.app_id] || 0) + 1; });

    // map counts back to unique_id (sum across app_ids for a student)
    const countsByUnique = {};
    uniqueList.forEach(u => countsByUnique[u] = 0);
    (apps||[]).forEach(a => {
      const c = countsByApp[a.app_id] || 0;
      const uid = studentIdMap[a.student_id];
      if(uid) countsByUnique[uid] = (countsByUnique[uid] || 0) + c;
    });

    return res.json(countsByUnique);
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Simple admin login (lookup staff by email) - sets session
app.post('/auth/login', async (req, res) => {
  try{
    const { email } = req.body;
    if(!email) return res.status(400).json({ error: 'email required' });
    const { data, error } = await supabase.from('staff').select('*').eq('email', email).limit(1).maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    if(!data) return res.status(401).json({ error: 'user not found' });
    // set session (minimal)
    req.session.user = { id: data.id, name: data.first_name ? (data.first_name + ' ' + (data.last_name||'')) : data.email, email: data.email };
    res.json({ ok: true, user: req.session.user });
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

app.post('/auth/logout', (req,res) => { req.session = null; res.json({ ok: true }); });

// Also provide a GET logout endpoint so static templates can link to it directly.
// Clears the session and redirects to the login/root page for browsers,
// or returns JSON for non-HTML clients (useful for SPA fetch-based logout).
app.get('/auth/logout', (req, res) => {
  try{
    req.session = null;
  }catch(e){ /* ignore */ }
  // If the client accepts HTML, redirect to root (login page). Otherwise return JSON.
  if(req.accepts && req.accepts('html')) return res.redirect('/');
  return res.json({ ok: true });
});

// Endpoint to inspect current session
app.get('/auth/me', (req,res) => { res.json({ user: req.session && req.session.user ? req.session.user : null }); });

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Server listening on http://localhost:${port}`));
