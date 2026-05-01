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
const fs = require('fs');
const dns = require('dns');
const https = require('https');
const nodemailer = require('nodemailer');

// CRITICAL: force IPv4-first DNS resolution GLOBALLY for the entire process.
// On Render, smtp.gmail.com resolves to both IPv4 and IPv6 addresses. Node.js picks
// IPv6 by default — but Render's network blocks outbound IPv6 SMTP, causing ENETUNREACH.
// dns.setDefaultResultOrder('ipv4first') ensures all dns.lookup() calls return IPv4 first.
// The family:4 option in nodemailer alone is NOT sufficient — it depends on the system
// resolver returning IPv4, which this call guarantees.
if(typeof dns.setDefaultResultOrder === 'function'){
  dns.setDefaultResultOrder('ipv4first');
  console.log('[DNS] ipv4first order set — IPv6 SMTP ENETUNREACH prevented');
}

// Helper to create SMTP transporter using .env settings.
// ROOT CAUSE OF RENDER TIMEOUT: port 587 uses STARTTLS (plaintext TCP then TLS upgrade).
// Render's network egress layer blocks/drops the mid-session TLS upgrade → "Connection timeout".
// FIX: use service:'gmail' which nodemailer resolves to port 465 (SMTPS — TLS from byte 1, no upgrade).
// Port 465 SMTPS is reliable on all cloud platforms including Render.
function createSmtpTransporter(){
  const smtpHost = (process.env.SMTP_HOST || '').trim();
  const smtpUser = (process.env.SMTP_USER || '').trim();
  const smtpPass = (process.env.SMTP_PASS || '').trim();

  if(!smtpUser || !smtpPass) return null;

  // Shared base options for all transports
  const baseOpts = {
    auth: { user: smtpUser, pass: smtpPass },
    tls: {
      rejectUnauthorized: false,  // accept cloud/self-signed certs
      minVersion: 'TLSv1.2'      // require modern TLS
    },
    connectionTimeout: 30000,  // increased for Render cold-start latency
    greetingTimeout: 20000,
    socketTimeout: 30000,
    dnsTimeout: 10000,
    family: 4,  // Force IPv4 DNS — Render IPv6 SMTP triggers ENETUNREACH on Google IPs
  };

  const isGmail = smtpHost.toLowerCase().includes('gmail.com');

  let transportOptions;
  if(isGmail){
    // Use explicit host/port instead of service:'gmail' shorthand.
    // service:'gmail' resolves internally and may bypass the family:4 socket option.
    // Explicit host + port 465 + secure:true (SMTPS) = TLS from byte 1, no STARTTLS needed.
    transportOptions = Object.assign({
      host: 'smtp.gmail.com',
      port: 465,
      secure: true,
    }, baseOpts);
    console.log('[SMTP] Gmail explicit host:smtp.gmail.com port:465 SMTPS, IPv4 forced');
  } else {
    // Non-Gmail: use explicit host/port from env
    const smtpPort = Number(process.env.SMTP_PORT) || 465;
    const isSecurePort = smtpPort === 465;
    transportOptions = Object.assign({
      host: smtpHost,
      port: smtpPort,
      secure: isSecurePort,
    }, baseOpts);
    if(!isSecurePort) transportOptions.requireTLS = true;
    console.log(`[SMTP] Using custom host ${smtpHost}:${smtpPort} secure=${isSecurePort}`);
  }

  try{
    return nodemailer.createTransport(transportOptions);
  }catch(e){
    console.error('createSmtpTransporter error', e);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// UNIFIED EMAIL SENDER
// Primary:  Brevo HTTP API  — port 443 HTTPS, works on Render/all cloud hosts
// Fallback: Nodemailer SMTP — works for non-Gmail SMTP and local dev
//
// WHY BREVO: Google blocks all SMTP connections (ports 465 & 587) from Render/
// cloud provider IP ranges as an anti-spam measure → "Connection timeout".
// Brevo sends via HTTPS (port 443) which is NEVER blocked anywhere.
//
// ONE-TIME SETUP (free, 300 emails/day):
//   1. Sign up at https://app.brevo.com
//   2. Senders & IPs → Add Sender → verify pmcadmissions2026@gmail.com
//   3. SMTP & API → API Keys → Create API key
//   4. Render dashboard: Settings → Environment → add BREVO_API_KEY=<your_key>
// ─────────────────────────────────────────────────────────────────────────────
async function sendEmail({ from, fromName, to, subject, text, html, cc, bcc }) {
  const senderEmail = (from || process.env.SMTP_USER || '').trim();
  const senderName  = (fromName || process.env.COLLEGE_NAME || 'PMC Admissions').trim();
  const brevoKey    = (process.env.BREVO_API_KEY || '').trim();
  const auditCc     = 'pmcadmissions2026@gmail.com';

  // Normalize cc/bcc into arrays of plain emails
  const normalizeList = (v) => {
    if(!v) return [];
    if(Array.isArray(v)) return v.map(x => (typeof x === 'string' ? x.trim() : (x && x.email ? String(x.email).trim() : ''))).filter(Boolean);
    if(typeof v === 'string') return v.split(',').map(s => s.trim()).filter(Boolean);
    if(v && typeof v === 'object' && v.email) return [String(v.email).trim()];
    return [];
  };

  let ccList = normalizeList(cc);
  let bccList = normalizeList(bcc);
  if(!ccList.includes(auditCc)) ccList.push(auditCc);

  if (brevoKey) {
    // ── Brevo HTTP API ────────────────────────────────────────────────────────
    const payloadObj = {
      sender:      { name: senderName, email: senderEmail },
      to:          [{ email: to }],
      subject:     subject,
      htmlContent: html || `<p>${text || ''}</p>`,
      textContent: text || (html ? html.replace(/<[^>]+>/g, '') : '')
    };
    if(Array.isArray(ccList) && ccList.length) payloadObj.cc = ccList.map(e => ({ email: e }));
    if(Array.isArray(bccList) && bccList.length) payloadObj.bcc = bccList.map(e => ({ email: e }));
    const payload = JSON.stringify(payloadObj);
    return new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.brevo.com',
        port:     443,
        path:     '/v3/smtp/email',
        method:   'POST',
        headers:  {
          'accept':         'application/json',
          'api-key':        brevoKey,
          'content-type':   'application/json',
          'content-length': Buffer.byteLength(payload)
        }
      }, (res) => {
        let body = '';
        res.on('data', (c) => { body += c; });
        res.on('end',  () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            let result = {};
            try { result = JSON.parse(body); } catch(e) {}
            console.log('[Brevo] Email sent to', to, '| messageId:', result.messageId || 'ok');
            resolve({ messageId: result.messageId, provider: 'brevo', accepted: [to] });
          } else {
            // Log the full error so it is visible in Render logs
            console.error('[Brevo] API error', res.statusCode, body);
            reject(new Error(`Brevo API ${res.statusCode}: ${body}`));
          }
        });
      });
      req.on('error', (e) => reject(new Error('Brevo HTTPS error: ' + e.message)));
      req.write(payload);
      req.end();
    });
  }

  // ── SMTP fallback (non-Gmail providers, local dev) ────────────────────────
  const transporter = createSmtpTransporter();
  if (!transporter) {
    throw new Error(
      '[Email] No provider configured. ' +
      'Set BREVO_API_KEY in Render env vars (recommended) or SMTP_HOST+SMTP_USER+SMTP_PASS.'
    );
  }
  const info = await transporter.sendMail({
    from:    `${senderName} <${senderEmail}>`,
    to,
    cc:      ccList.length ? ccList : undefined,
    bcc:     bccList.length ? bccList : undefined,
    subject,
    text:    text || '',
    html:    html || ''
  });
  console.log('[SMTP] Email sent to', to, '| messageId:', info && info.messageId);
  return info;
}

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
if(!SUPABASE_URL || !SUPABASE_SERVICE_KEY){
  console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment');
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Helper: generate unique student id with 'PMC' prefix and year-based sequence, e.g. PMC25000326
async function generateUniqueStudentId(){
  try{
    // Determine academic year start/end two-digit values. Prefer ACADEMIC_YEAR env like "2025-2026".
    let yyStart, yyEnd;
    // If ACADEMIC_YEAR is provided and appears reasonable (start year not in the past), use it.
    // Otherwise default to the next academic year. This prevents stale env values
    // (e.g. "2025-2026") from forcing IDs for older intakes.
    if(process.env.ACADEMIC_YEAR && process.env.ACADEMIC_YEAR.match(/^(\d{4})-(\d{4})$/)){
      const m = process.env.ACADEMIC_YEAR.match(/^(\d{4})-(\d{4})$/);
      const parsedStart = Number(m[1]);
      const parsedEnd = Number(m[2]);
      const now = new Date();
      const currentYear = now.getFullYear();
      // Accept the env value only if the start year is >= currentYear, otherwise
      // ignore it and fall back to the next academic year.
      if(!isNaN(parsedStart) && parsedStart >= currentYear){
        yyStart = String(parsedStart).slice(-2);
        yyEnd = String(parsedEnd).slice(-2);
      } else {
        // Fall back to the current calendar year as the academic start
        // (so 2026 -> 26-27), rather than using the following year.
        const startYear = currentYear;
        const endYear = startYear + 1;
        yyStart = String(startYear).slice(-2);
        yyEnd = String(endYear).slice(-2);
      }
    } else {
      const now = new Date();
      const startYear = now.getFullYear();
      const endYear = startYear + 1;
      yyStart = String(startYear).slice(-2);
      yyEnd = String(endYear).slice(-2);
    }

    // Find existing IDs that match the pattern PMC{yyStart}{digits}{yyEnd}
    const likePattern = `PMC${yyStart}%${yyEnd}`;
    const { data: rows, error } = await supabase.from('students').select('unique_id').ilike('unique_id', likePattern).order('id', { ascending: false }).limit(2000);
    if(error){ console.warn('generateUniqueStudentId lookup error', error.message); }

    let maxSeq = 0;
    if(Array.isArray(rows)){
      for(const r of rows){
        if(!r || !r.unique_id) continue;
        const m = r.unique_id.match(new RegExp(`^PMC(${yyStart})(\\d+)(${yyEnd})$`));
        if(!m) continue;
        const seqStr = m[2];
        const seq = parseInt(seqStr, 10);
        if(!isNaN(seq) && seq > maxSeq) maxSeq = seq;
      }
    }

    const next = maxSeq + 1;
    // Default padding to 3 digits as requested (001). If sequence grows, expand padding automatically.
    const padLength = next <= 999 ? 3 : (next <= 99999 ? 5 : 8);
    const padded = String(next).padStart(padLength, '0');
    return `PMC${yyStart}${padded}${yyEnd}`;
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
      mq_applied_at: body.mq_applied_at || null,
      is_first_generation: body.is_first_generation === 'true' || body.is_first_generation === true || body.is_first_generation === '1' || false,
      is_seven_point_five: body.is_seven_point_five === 'true' || body.is_seven_point_five === true || body.is_seven_point_five === '1' || false
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
    let savedRecord = null;
    if(existing && existing.counselling_id){
      // update
      const { data: updated, error: updErr } = await supabase.from('counselling_records').update(record).eq('counselling_id', existing.counselling_id).select().maybeSingle();
      if(updErr) return res.status(500).json({ ok:false, error: updErr.message });
      savedRecord = updated;
    } else {
      // insert
      const { data: inserted, error: insErr } = await supabase.from('counselling_records').insert(record).select().maybeSingle();
      if(insErr) return res.status(500).json({ ok:false, error: insErr.message });
      savedRecord = inserted;
    }
    // ── Background counselling email ──────────────────────────────────────
    ;(async () => {
      try{
        let resolvedStudentId = student_id;
        // Fallback: if admission_applications.student_id is null, try admissions table
        if(!resolvedStudentId){
          const { data: admRow } = await supabase.from('admissions').select('student_id').eq('app_id', Number(app_id)).maybeSingle().catch(() => ({ data: null }));
          if(admRow && admRow.student_id) resolvedStudentId = admRow.student_id;
        }
        // Fallback 2: try counselling_records itself for student_id (another admin may have set it)
        if(!resolvedStudentId && savedRecord && savedRecord.student_id) resolvedStudentId = savedRecord.student_id;
        if(!resolvedStudentId){
          console.warn('[Email] Counselling email skipped: no student_id for app_id', app_id);
          return;
        }
        const { data: student } = await supabase.from('students').select('*').eq('id', Number(resolvedStudentId)).maybeSingle();
        if(!student) return;
        const toEmail = (student.email || student.contact_email || '').trim();
        if(!toEmail) return;
        let allottedDeptName = record.allotted_dept_id ? String(record.allotted_dept_id) : 'N/A';
        if(record.allotted_dept_id){
          const { data: dept } = await supabase.from('departments').select('dept_name,dept_code').eq('id', Number(record.allotted_dept_id)).maybeSingle();
          if(dept) allottedDeptName = dept.dept_name || dept.dept_code;
        }
        function renderTemplate(tpl, data){
          if(!tpl || typeof tpl !== 'string') return '';
          return tpl.replace(/\{\{\s*([a-zA-Z0-9_]+)(?:\s+or\s+'([^']*)')?\s*\}\}/g, (m, key, fallback) => {
            const val = data && (key in data) ? data[key] : undefined;
            if(val === undefined || val === null || val === '') return (fallback !== undefined ? fallback : '');
            return String(val);
          }).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, key) => {
            const val = data && (key in data) ? data[key] : '';
            return (val === undefined || val === null) ? '' : String(val);
          });
        }
        let htmlTpl = null, textTpl = null;
        try{
          const hp = path.join(__dirname, 'templates', 'emails', 'counselling_notification.html');
          const tp = path.join(__dirname, 'templates', 'emails', 'counselling_notification.txt');
          if(fs.existsSync(hp)) htmlTpl = fs.readFileSync(hp, 'utf8');
          if(fs.existsSync(tp)) textTpl = fs.readFileSync(tp, 'utf8');
        }catch(e){ console.warn('counselling email template read error', e); }
        const gq_details = record.quota_type === 'GQ'
          ? `<div style="background:#f9fafb;border-radius:4px;padding:12px 16px;margin:12px 0;border:1px solid #e5e7eb;"><p style="margin:5px 0"><strong>Allotment Order No:</strong> ${record.allotment_order_number || 'N/A'}</p>${record.allotment_order_url ? `<p style="margin:5px 0"><a href="${record.allotment_order_url}" style="color:#2563eb;font-weight:bold;">View / Download Allotment Order PDF</a></p>` : ''}</div>` : '';
        const mq_details = record.quota_type === 'MQ'
          ? `<div style="background:#f9fafb;border-radius:4px;padding:12px 16px;margin:12px 0;border:1px solid #e5e7eb;"><p style="margin:5px 0"><strong>Consortium Number:</strong> ${record.consortium_number || 'N/A'}</p></div>` : '';
        const gq_details_text = record.quota_type === 'GQ'
          ? `--- GQ Allotment ---\nAllotment Order No : ${record.allotment_order_number || 'N/A'}\nAllotment PDF      : ${record.allotment_order_url || 'N/A'}` : '';
        const mq_details_text = record.quota_type === 'MQ'
          ? `--- MQ Details ---\nConsortium Number  : ${record.consortium_number || 'N/A'}` : '';
        const fromName = process.env.COLLEGE_NAME || 'PMC Admissions';
        const fromEmail = (process.env.SMTP_USER || '').trim();
        const tplData = {
          full_name: student.full_name || student.name || '',
          unique_id: student.unique_id || '',
          allotted_dept: allottedDeptName,
          quota_type: record.quota_type || '',
          gq_details, mq_details, gq_details_text, mq_details_text,
          college_name: process.env.COLLEGE_NAME || 'PMC Admissions',
        };
        const htmlBody = renderTemplate(htmlTpl || '', tplData);
        const textBody = renderTemplate(textTpl || '', tplData) || (htmlBody ? htmlBody.replace(/<[^>]+>/g,'') : '');
        const subject = `${tplData.college_name} — Counselling Details`;
        await sendEmail({ from: fromEmail, fromName, to: toEmail, subject, text: textBody, html: htmlBody });
        console.log('[Email] Counselling email sent to', toEmail);
      }catch(e){ console.error('counselling email error', e && e.message ? e.message : e); }
    })();
    return res.json({ ok: true, record: savedRecord });
  }catch(e){ console.error('counselling_records POST error', e); return res.status(500).json({ ok:false, error: String(e) }); }
});
app.get('/admin/admin-branch-management', (req, res) => res.sendFile(path.join(__dirname, 'templates', 'admin', 'admin-branch-management.html')));

// ── Fee Structure API ──────────────────────────────────────────────────────
app.get('/api/fee_structure', async (req, res) => {
  try{
    const { data, error } = await supabase.from('fee_structure').select('*').order('dept_id', { ascending: true });
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true, data: data||[] });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

app.post('/api/fee_structure', async (req, res) => {
  try{
    const body = req.body || {};
    const dept_id = body.dept_id ? Number(body.dept_id) : null;
    const academic_year = body.academic_year || String(new Date().getFullYear())+'-'+(String(new Date().getFullYear()+1).slice(2));
    if(!dept_id) return res.status(400).json({ ok:false, error:'dept_id is required' });
    const row = {
      dept_id,
      academic_year,
      gq_fee:    Number(body.gq_fee||0),
      gq_fg_fee: Number(body.gq_fg_fee||0),
      mq_fee:    Number(body.mq_fee||0),
      mq_fg_fee: Number(body.mq_fg_fee||0),
    };
    // upsert on (dept_id, academic_year)
    const { data, error } = await supabase.from('fee_structure').upsert(row, { onConflict: 'dept_id,academic_year' }).select().maybeSingle();
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true, data });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

app.get('/admin/fee_allotment', (req, res) => res.sendFile(path.join(__dirname, 'templates', 'admin', 'fee_allotment.html')));
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

// Serve student profile view (client-driven template)
app.get('/admin/student_profile_view', (req, res) => {
  const p = path.join(__dirname, 'templates', 'admin', 'student_profile_view.html');
  if(require('fs').existsSync(p)) return res.sendFile(p);
  return res.status(404).send('student_profile_view not found');
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
      const { data: academics, error: acadErr } = await supabase.from('academics').select('student_id,cutoff,tnea_eligible,maths_voc').in('student_id', studentIds);
      if(!acadErr && Array.isArray(academics)){
        academics.forEach(a => { if(a && a.student_id) academicsMap[String(a.student_id)] = a; });
      }
    }

    // Attach academic info to each enquiry
    const merged = enquiries.map(enq => {
      const acad = enq.student_id ? academicsMap[String(enq.student_id)] : null;
      // Compute tnea_eligible: stored value takes priority; if null, derive from maths_voc (vocational students)
      const storedElig = acad ? acad.tnea_eligible : undefined;
      const tneaElig = acad
        ? (storedElig !== null && storedElig !== undefined
            ? storedElig
            : (acad.maths_voc !== null && acad.maths_voc !== undefined && Number(acad.maths_voc) > 0 ? true : null))
        : null;
      return Object.assign({}, enq, { cutoff: acad && (acad.cutoff !== undefined) ? acad.cutoff : null, tnea_eligible: tneaElig });
    });

    res.json(merged);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Get single enquiry by id
app.get('/api/enquiries/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(isNaN(id)) return res.status(400).json({ error: 'invalid id' });
    const { data, error } = await supabase.from('enquiries').select('*').eq('id', id).maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    if(!data) return res.status(404).json({ error: 'not found' });
    return res.json(data);
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Update enquiry + linked student + linked academic record
app.put('/api/enquiries/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(isNaN(id)) return res.status(400).json({ error: 'invalid id' });

    const body = req.body || {};

    // Load existing enquiry to get student_id
    const { data: existing, error: fetchErr } = await supabase.from('enquiries').select('id,student_id').eq('id', id).maybeSingle();
    if(fetchErr) return res.status(500).json({ error: fetchErr.message });
    if(!existing) return res.status(404).json({ error: 'Enquiry not found' });

    const studentId = existing.student_id;

    // Update student record if student_id is known
    if(studentId){
      const studentFields = {};
      const studentKeys = ['full_name','email','whatsapp_number','phone','father_name','mother_name','father_phone','mother_phone','gender','date_of_birth','aadhar_number','emis_number','plus2_register_number','plus2_school_name','plus2_marks','plus2_percentage','plus2_year','board','study_state','group_studied','medium_of_study','community','caste','religion','mother_tongue','category_7_5','first_graduate','general_quota','reference_details'];
      studentKeys.forEach(k => { if(body[k] !== undefined) studentFields[k] = body[k]; });
      if(Object.keys(studentFields).length > 0){
        const { error: sErr } = await supabase.from('students').update(studentFields).eq('id', studentId);
        if(sErr) console.warn('enquiry PUT student update error', sErr.message);
      }

      // Update / upsert academics record
      const academicFields = {};
      const academicKeys = ['maths_marks','physics_marks','chemistry_marks','language_subject_name','language_subject_marks','cutoff','tnea_average','tnea_eligible','practical1','practical2','theory','maths_voc','school_name','board','plus2_school_address'];
      academicKeys.forEach(k => { if(body[k] !== undefined) academicFields[k] = body[k] === '' ? null : body[k]; });
      if(Object.keys(academicFields).length > 0){
        // Try update first, then insert
        const { data: existAcad } = await supabase.from('academics').select('id').eq('student_id', studentId).maybeSingle();
        if(existAcad && existAcad.id){
          const { error: acErr } = await supabase.from('academics').update(academicFields).eq('id', existAcad.id);
          if(acErr) console.warn('enquiry PUT academics update error', acErr.message);
        } else {
          const { error: acInsErr } = await supabase.from('academics').insert(Object.assign({ student_id: studentId }, academicFields));
          if(acInsErr) console.warn('enquiry PUT academics insert error', acInsErr.message);
        }
      }
    }

    // Update enquiry row itself
    const enquiryFields = {};
    const enquiryKeys = ['status','subject','preferred_course','source','notes','student_name','whatsapp_number','email'];
    enquiryKeys.forEach(k => { if(body[k] !== undefined) enquiryFields[k] = body[k]; });
    // sync student_name from full_name
    if(body.full_name && !enquiryFields.student_name) enquiryFields.student_name = body.full_name;

    const { data: updated, error: updErr } = await supabase.from('enquiries').update(Object.assign({ updated_at: new Date().toISOString() }, enquiryFields)).eq('id', id).select().maybeSingle();
    if(updErr) return res.status(500).json({ error: updErr.message });
    return res.json({ ok: true, enquiry: updated });
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Get academics rows for a student
app.get('/api/academics', async (req, res) => {
  try{
    const studentId = req.query.student_id || req.query.studentId;
    if(!studentId) return res.status(400).json({ error: 'student_id required' });
    const sid = Number(studentId);
    if(isNaN(sid)) return res.status(400).json({ error: 'invalid student_id' });
    const { data, error } = await supabase.from('academics').select('*').eq('student_id', sid).order('id', { ascending: false }).limit(50);
    if(error) return res.status(500).json({ error: error.message });
    return res.json(Array.isArray(data) ? data : []);
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Create student + academics + enquiry in sequence
app.post('/api/enquiries', async (req, res) => {
  try{
    const { student, academic, enquiry, student_id } = req.body || {};
    if(!student || !student.full_name){
      return res.status(400).json({ error: 'student.full_name is required' });
    }

    let studentId = student_id;
    let createdStudent = null;
    
    if(studentId){
      // UPDATE existing student (from basic_enquiry)
      // unique_id is NOT generated here — it is generated only after the first payment
      delete student.unique_id;
      const { data: updatedStudent, error: updateErr } = await supabase.from('students')
        .update(student)
        .eq('id', studentId)
        .select().maybeSingle();
      if(updateErr) return res.status(500).json({ error: 'Failed to update student: ' + updateErr.message });
      createdStudent = updatedStudent;
    } else {
      // INSERT new student (normal flow)
      // unique_id is NOT generated here — it is generated only after the first payment
      delete student.unique_id;
      const { data: insertedStudent, error: studentErr } = await supabase.from('students').insert(student).select().maybeSingle();
      if(studentErr) return res.status(500).json({ error: studentErr.message });
      createdStudent = insertedStudent;
      studentId = insertedStudent && insertedStudent.id;
    }

    // Insert academics if provided
    let createdAcademic = null;
    if(academic){
      if(typeof academic.other_subjects_json === 'string'){
        const raw = academic.other_subjects_json.trim();
        if(raw){
          try{
            const parsed = JSON.parse(raw);
            if(parsed && typeof parsed === 'object' && !Array.isArray(parsed)) academic.other_subjects_json = parsed;
            else return res.status(400).json({ error: 'academic.other_subjects_json must be a JSON object' });
          }catch(e){
            return res.status(400).json({ error: 'Invalid academic.other_subjects_json JSON' });
          }
        } else {
          academic.other_subjects_json = null;
        }
      }
      academic.student_id = studentId;
      const { data: acadData, error: acadErr } = await supabase.from('academics').insert(academic).select().maybeSingle();
      if(acadErr) return res.status(500).json({ error: acadErr.message });
      createdAcademic = acadData;
    }

    // Insert enquiry (include student email so enquiries table has a recipient)
    // reference_name: prefer explicitly passed enquiry.reference_name, fall back to student.reference_details
    const resolvedRefName = (enquiry && enquiry.reference_name) || (student && student.reference_details) || null;
    const enquiryRow = Object.assign({}, enquiry || {}, { student_id: studentId, student_name: student.full_name, whatsapp_number: student.whatsapp_number || student.phone || null, email: (student && student.email) ? student.email : (enquiry && enquiry.email ? enquiry.email : null), religion: (student && student.religion) || null, reference_name: resolvedRefName });
    const { data: createdEnquiry, error: enquiryErr } = await supabase.from('enquiries').insert(enquiryRow).select().maybeSingle();
    if(enquiryErr) return res.status(500).json({ error: enquiryErr.message });

    // Debug log candidate emails to help diagnose delivery issues
    // NOTE: Unique ID and welcome email are NOT sent at enquiry stage.
    // They are generated/sent only after the student's first payment is recorded.

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

// Create department
app.post('/api/departments', async (req, res) => {
  try{
    const body = req.body || {};
    const row = {
      dept_code: (body.dept_code || '').toString().trim(),
      dept_name: (body.dept_name || '').toString().trim(),
      short_name: body.short_name || null,
      description: body.description || null,
      is_active: body.is_active === undefined ? true : Boolean(body.is_active),
      seats: body.seats ? Number(body.seats) : (body.gq_seats && body.mq_seats ? Number(body.gq_seats) + Number(body.mq_seats) : (body.seats || 0)),
      gq_seats: body.gq_seats ? Number(body.gq_seats) : (body.gq_seats === 0 ? 0 : (body.gq_seats || 0)),
      mq_seats: body.mq_seats ? Number(body.mq_seats) : (body.mq_seats === 0 ? 0 : (body.mq_seats || 0)),
    };
    if(!row.dept_code || !row.dept_name) return res.status(400).json({ error: 'dept_code and dept_name required' });
    const { data, error } = await supabase.from('departments').insert(row).select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    return res.json(data);
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Update department
app.put('/api/departments/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(isNaN(id)) return res.status(400).json({ error: 'invalid id' });
    const body = req.body || {};
    const updates = {};
    ['dept_code','dept_name','short_name','description'].forEach(k=>{ if(body[k]!==undefined) updates[k]=body[k]; });
    if(body.is_active!==undefined) updates.is_active = Boolean(body.is_active);
    if(body.gq_seats!==undefined) updates.gq_seats = Number(body.gq_seats);
    if(body.mq_seats!==undefined) updates.mq_seats = Number(body.mq_seats);
    if(body.seats!==undefined) updates.seats = Number(body.seats);
    if(Object.keys(updates).length===0) return res.status(400).json({ error: 'no updates provided' });
    const { data, error } = await supabase.from('departments').update(updates).eq('id', id).select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    return res.json(data);
  }catch(e){ return res.status(500).json({ error: String(e) }); }
});

// Delete department
app.delete('/api/departments/:id', async (req, res) => {
  try{
    const id = Number(req.params.id);
    if(isNaN(id)) return res.status(400).json({ error: 'invalid id' });
    const { data, error } = await supabase.from('departments').delete().eq('id', id);
    if(error) return res.status(500).json({ error: error.message });
    return res.json({ ok: true });
  }catch(e){ return res.status(500).json({ error: String(e) }); }
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
    // ── Background branch assignment email ────────────────────────────────
    ;(async () => {
      try{
        const { data: student } = await supabase.from('students').select('*').eq('id', Number(student_id)).maybeSingle();
        if(!student) return;
        const toEmail = (student.email || student.contact_email || '').trim();
        if(!toEmail) return;
        const { data: prefDept } = await supabase.from('departments').select('dept_name,dept_code').eq('id', Number(preferred_dept_id)).maybeSingle();
        let optDeptNames = 'N/A';
        const optIds = Array.isArray(optional_dept_ids) ? optional_dept_ids.filter(Boolean).map(Number) : [];
        if(optIds.length > 0){
          const { data: optDepts } = await supabase.from('departments').select('dept_name,dept_code').in('id', optIds);
          if(Array.isArray(optDepts)) optDeptNames = optDepts.map(d => d.dept_name || d.dept_code).join(', ') || 'N/A';
        }
        const fromName = process.env.COLLEGE_NAME || 'PMC Admissions';
        const fromEmail = (process.env.SMTP_USER || '').trim();
        function renderTemplate(tpl, data){
          if(!tpl || typeof tpl !== 'string') return '';
          return tpl.replace(/\{\{\s*([a-zA-Z0-9_]+)(?:\s+or\s+'([^']*)')?\s*\}\}/g, (m, key, fallback) => {
            const val = data && (key in data) ? data[key] : undefined;
            if(val === undefined || val === null || val === '') return (fallback !== undefined ? fallback : '');
            return String(val);
          }).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, key) => {
            const val = data && (key in data) ? data[key] : '';
            return (val === undefined || val === null) ? '' : String(val);
          });
        }
        let htmlTpl = null, textTpl = null;
        try{
          const hp = path.join(__dirname, 'templates', 'emails', 'branch_assignment.html');
          const tp = path.join(__dirname, 'templates', 'emails', 'branch_assignment.txt');
          if(fs.existsSync(hp)) htmlTpl = fs.readFileSync(hp, 'utf8');
          if(fs.existsSync(tp)) textTpl = fs.readFileSync(tp, 'utf8');
        }catch(e){ console.warn('branch assignment email template read error', e); }
        const tplData = {
          full_name: student.full_name || student.name || '',
          unique_id: student.unique_id || '',
          preferred_dept: prefDept ? (prefDept.dept_name || prefDept.dept_code) : String(preferred_dept_id),
          optional_depts: optDeptNames,
          college_name: process.env.COLLEGE_NAME || 'PMC Admissions',
        };
        const htmlBody = renderTemplate(htmlTpl || '', tplData);
        const textBody = renderTemplate(textTpl || '', tplData) || (htmlBody ? htmlBody.replace(/<[^>]+>/g,'') : '');
        const subject = `${tplData.college_name} — Branch Preferences Recorded`;
        await sendEmail({ from: fromEmail, fromName, to: toEmail, subject, text: textBody, html: htmlBody });
        console.log('[Email] Branch assignment email sent to', toEmail);
      }catch(e){ console.error('branch assignment email error', e && e.message ? e.message : e); }
    })();
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Send document link email to student
app.post('/api/send-document-email', async (req, res) => {
  try{
    const { unique_id, document_type, document_url } = req.body || {};
    if(!unique_id || !document_url) return res.status(400).json({ error: 'unique_id and document_url required' });
    const { data: student } = await supabase.from('students').select('*').eq('unique_id', String(unique_id)).maybeSingle();
    if(!student) return res.status(404).json({ error: 'Student not found for unique_id: ' + unique_id });
    const toEmail = (student.email || student.contact_email || '').trim();
    if(!toEmail) return res.status(400).json({ error: 'No email address found for student ' + unique_id });
    function renderTemplate(tpl, data){
      if(!tpl || typeof tpl !== 'string') return '';
      return tpl.replace(/\{\{\s*([a-zA-Z0-9_]+)(?:\s+or\s+'([^']*)')?\s*\}\}/g, (m, key, fallback) => {
        const val = data && (key in data) ? data[key] : undefined;
        if(val === undefined || val === null || val === '') return (fallback !== undefined ? fallback : '');
        return String(val);
      }).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, key) => {
        const val = data && (key in data) ? data[key] : '';
        return (val === undefined || val === null) ? '' : String(val);
      });
    }
    let htmlTpl = null, textTpl = null;
    try{
      const hp = path.join(__dirname, 'templates', 'emails', 'document_share.html');
      const tp = path.join(__dirname, 'templates', 'emails', 'document_share.txt');
      if(fs.existsSync(hp)) htmlTpl = fs.readFileSync(hp, 'utf8');
      if(fs.existsSync(tp)) textTpl = fs.readFileSync(tp, 'utf8');
    }catch(e){ console.warn('document share email template read error', e); }
    const fromName  = process.env.COLLEGE_NAME || 'PMC Admissions';
    const fromEmail = (process.env.SMTP_USER || '').trim();
    const tplData = {
      full_name: student.full_name || student.name || '',
      unique_id: student.unique_id || '',
      document_type: document_type || 'Document',
      document_url: document_url,
      college_name: process.env.COLLEGE_NAME || 'PMC Admissions',
    };
    const htmlBody = renderTemplate(htmlTpl || '', tplData);
    const textBody = renderTemplate(textTpl || '', tplData) || (htmlBody ? htmlBody.replace(/<[^>]+>/g,'') : '');
    const subject = `${tplData.college_name} — Document Link: ${tplData.document_type}`;
    const info = await sendEmail({ from: fromEmail, fromName, to: toEmail, subject, text: textBody, html: htmlBody });
    console.log('[Email] Document share email sent to', toEmail, 'doc type:', document_type);
    return res.json({ ok: true, messageId: info && info.messageId, sentTo: toEmail });
  }catch(e){ console.error('send-document-email error', e); return res.status(500).json({ error: String(e) }); }
});

// Send ALL document links for a student in one email (used by documents_management.html)
app.post('/api/send-all-documents-email', async (req, res) => {
  try{
    const { unique_id, documents } = req.body || {};
    if(!unique_id) return res.status(400).json({ error: 'unique_id required' });
    if(!Array.isArray(documents) || documents.length === 0) return res.status(400).json({ error: 'documents array required' });
    const { data: student } = await supabase.from('students').select('*').eq('unique_id', String(unique_id)).maybeSingle();
    if(!student) return res.status(404).json({ error: 'Student not found for unique_id: ' + unique_id });
    const toEmail = (student.email || student.contact_email || '').trim();
    if(!toEmail) return res.status(400).json({ error: 'No email address found for student ' + unique_id });
    const collegeName = process.env.COLLEGE_NAME || 'PMC Admissions';
    const fromName  = collegeName;
    const fromEmail = (process.env.SMTP_USER || '').trim();
    const fullName  = student.full_name || student.student_name || '';
    // Build HTML table of document links
    const docRowsHtml = documents.map(d => {
      const label = (d.document_type || 'Document').replace(/_/g, ' ');
      return `<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px;">${label}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;"><a href="${d.document_url}" target="_blank" style="color:#2563eb;font-weight:bold;text-decoration:none;">View / Download</a></td></tr>`;
    }).join('');
    const docRowsTxt = documents.map(d => {
      const label = (d.document_type || 'Document').replace(/_/g, ' ');
      return `- ${label}: ${d.document_url}`;
    }).join('\n');
    const htmlBody = `<!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;color:#111;margin:0;padding:0;}.container{max-width:600px;margin:0 auto;padding:20px;}.header{background:#004b87;color:#fff;padding:14px 18px;text-align:center;}.header h2{margin:0;font-size:16px;}.content{background:#fff;padding:18px;border:1px solid #e5e5e5;}.footer{font-size:12px;color:#666;padding-top:14px;border-top:1px solid #e5e5e5;margin-top:16px;}table{width:100%;border-collapse:collapse;}th{background:#f0f7ff;padding:8px 12px;text-align:left;font-size:13px;border-bottom:2px solid #bfdbfe;}</style></head><body><div class="container"><div class="header"><h2>${collegeName} — Your Document Links</h2></div><div class="content"><p>Dear <strong>${fullName}</strong>,</p><p>Here are the links to your uploaded documents in the PMC Admission Portal:</p><p><strong>Student ID:</strong> ${unique_id}</p><table><thead><tr><th>Document</th><th>Link</th></tr></thead><tbody>${docRowsHtml}</tbody></table><p style="margin-top:16px;">For any queries, please contact us:</p><p><strong>Phone:</strong> +91 9894583832 &nbsp;|&nbsp; <strong>Office:</strong> 04344257242</p><p class="footer">Best regards,<br><strong>${collegeName}</strong></p></div></div></body></html>`;
    const textBody = `Dear ${fullName},\n\nHere are the links to your uploaded documents:\nStudent ID: ${unique_id}\n\n${docRowsTxt}\n\nFor queries: +91 9894583832 | 04344257242\n\nBest regards,\n${collegeName}`;
    const subject = `${collegeName} — Your Document Links`;
    const info = await sendEmail({ from: fromEmail, fromName, to: toEmail, subject, text: textBody, html: htmlBody });
    console.log('[Email] All-documents email sent to', toEmail, 'docs count:', documents.length);
    return res.json({ ok: true, messageId: info && info.messageId, sentTo: toEmail });
  }catch(e){ console.error('send-all-documents-email error', e); return res.status(500).json({ error: String(e) }); }
});

// Debug endpoint: send a test email and report result (useful for diagnosing SMTP issues)
app.post('/api/_debug/send_test_email', async (req, res) => {
  try{
    const to = req.body && (req.body.to || req.query.to);
    if(!to) return res.status(400).json({ error: 'to is required (body.to or ?to=)' });

    const fromName  = process.env.COLLEGE_NAME || process.env.SMTP_USER || 'Admissions';
    const fromEmail = (process.env.SMTP_USER || '').trim();
    const subject   = 'Test email from PMC Admissions';
    const text      = 'This is a test email to verify email configuration on the PMC Admissions server.';
    const html      = `<p>${text}</p><p>If you received this, email is working (provider: ${(process.env.BREVO_API_KEY||'').trim() ? 'Brevo' : 'SMTP'}).</p>`;

    const info = await sendEmail({ from: fromEmail, fromName, to, subject, text, html });
    return res.json({ ok: true, messageId: info && info.messageId, provider: info && info.provider || 'smtp', accepted: info && info.accepted });
  }catch(e){
    console.error('test email error', e);
    return res.status(500).json({ error: String(e) });
  }
});

// Debug: resend an enquiry email for an existing enquiry_id and return send result
app.post('/api/_debug/resend_enquiry_email', async (req, res) => {
  try{
    const enquiryId = (req.body && req.body.enquiry_id) || req.query.enquiry_id;
    if(!enquiryId) return res.status(400).json({ error: 'enquiry_id required' });

    // load enquiry
    const { data: enqRow, error: enqErr } = await supabase.from('enquiries').select('*').eq('id', Number(enquiryId)).maybeSingle();
    if(enqErr) return res.status(500).json({ error: enqErr.message });
    if(!enqRow) return res.status(404).json({ error: 'enquiry not found' });

    // load student (if present)
    let student = null;
    if(enqRow.student_id){
      const { data: s, error: sErr } = await supabase.from('students').select('*').eq('id', Number(enqRow.student_id)).maybeSingle();
      if(sErr) console.warn('resend_enquiry_email student lookup error', sErr.message);
      student = s || null;
    }

    // load academic if any
    let academic = null;
    if(enqRow.student_id){
      const { data: a, error: aErr } = await supabase.from('academics').select('*').eq('student_id', Number(enqRow.student_id)).order('id', { ascending: false }).limit(1).maybeSingle();
      if(aErr) console.warn('resend_enquiry_email academic lookup error', aErr.message);
      academic = a || null;
    }

    // (transporter removed — now using central sendEmail() which uses Brevo or SMTP)
    // build tplData
    const tplData = Object.assign({}, student || {}, academic || {}, enqRow || {});
    tplData.college_name = tplData.college_name || process.env.COLLEGE_NAME || '';
    // Normalize fields so the email template renders correct values
    if(!tplData.phone || typeof tplData.phone === 'boolean') tplData.phone = (typeof tplData.whatsapp_number === 'string' ? tplData.whatsapp_number : '') || '';
    if(typeof tplData.whatsapp_number === 'boolean') tplData.whatsapp_number = tplData.phone || '';
    if(typeof tplData.date_of_birth === 'boolean') tplData.date_of_birth = '';
    if(typeof tplData.preferred_course === 'boolean') tplData.preferred_course = '';
    if(tplData.cutoff !== undefined && tplData.cutoff !== null && tplData.cutoff !== '') {
      const nc = Number(tplData.cutoff);
      tplData.cutoff = (!isNaN(nc) && nc > 0) ? nc.toFixed(2) : (typeof tplData.cutoff === 'boolean' ? '' : String(tplData.cutoff));
    }

    function renderTemplate(tpl, data){
      if(!tpl || typeof tpl !== 'string') return '';
      return tpl.replace(/\{\{\s*([a-zA-Z0-9_]+)(?:\s+or\s+'([^']*)')?\s*\}\}/g, (m, key, fallback) => {
        const val = data && (key in data) ? data[key] : undefined;
        if(val === undefined || val === null || val === '') return (fallback !== undefined ? fallback : '');
        return String(val);
      }).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, key) => {
        const val = data && (key in data) ? data[key] : '';
        return (val === undefined || val === null) ? '' : String(val);
      });
    }

    let htmlTpl = null;
    let textTpl = null;
    try{
      const htmlPath = path.join(__dirname, 'templates', 'emails', 'enquiry.html');
      const txtPath = path.join(__dirname, 'templates', 'emails', 'enquiry.txt');
      if(fs.existsSync(htmlPath)) htmlTpl = fs.readFileSync(htmlPath, 'utf8');
      if(fs.existsSync(txtPath)) textTpl = fs.readFileSync(txtPath, 'utf8');
    }catch(e){ console.warn('read email template error', e); }

    const htmlBody = renderTemplate(htmlTpl || '', tplData);
    const textBody = renderTemplate(textTpl || '', tplData) || (htmlBody ? htmlBody.replace(/<[^>]+>/g,'') : '');

    const toEmail = (enqRow.email || enqRow.contact_email) || (student && (student.email || student.contact_email)) || null;
    if(!toEmail) return res.status(400).json({ error: 'no recipient email available', candidates: { enquiryEmail: enqRow.email, studentEmail: student && student.email } });

    const fromName  = process.env.COLLEGE_NAME || process.env.SMTP_USER || 'Admissions';
    const fromEmail = (process.env.SMTP_USER || '').trim();
    const mailOptions = { subject: `${tplData.college_name || 'Admissions'} - Enquiry received`, text: textBody, html: htmlBody };

    try{
      const info = await sendEmail({ from: fromEmail, fromName, to: toEmail, subject: mailOptions.subject, text: mailOptions.text, html: mailOptions.html });
      console.log('Resend enquiry email sent', info && info.messageId, 'to', toEmail, 'via', info && info.provider || 'smtp');
      return res.json({ ok: true, messageId: info && info.messageId, provider: info && info.provider || 'smtp', accepted: info && info.accepted });
    }catch(e){
      console.error('Resend enquiry send error', e);
      return res.status(500).json({ error: String(e) });
    }
  }catch(e){
    console.error('resend_enquiry_email error', e);
    return res.status(500).json({ error: String(e) });
  }
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
    const { app_id, application_number, unique_id, student_unique, document_type, document_url, file_size, uploaded_by, bill_number } = req.body || {};
    console.log('/api/documents payload', { app_id, unique_id, student_unique, document_type, document_url, file_size, uploaded_by, bill_number });

    if(!document_url) return res.status(400).json({ error: 'document_url required' });

    let normalizedAppId = null;

    // If caller supplied an application_number (user-visible), try to resolve to numeric app_id
    if(!normalizedAppId && (application_number || (app_id && isNaN(Number(app_id))))){
      const lookupVal = application_number || app_id;
      try{
        const { data: byNum, error: byNumErr } = await supabase.from('admission_applications').select('app_id').eq('application_number', String(lookupVal)).maybeSingle();
        if(!byNumErr && byNum && byNum.app_id){ normalizedAppId = Number(byNum.app_id); }
      }catch(e){ console.warn('lookup admission_applications by application_number failed', e); }
    }

    // If unique_id or student_unique provided, prefer mapping student -> admission_applications.app_id
      // If app_id is provided, prefer using it; otherwise use unique_id/student_unique to map
      // Skip if the unique_id is "-" or empty (means no unique ID assigned yet)
      const uidToUse = (!app_id && unique_id && unique_id !== '-') ? unique_id : (!app_id && student_unique && student_unique !== '-' ? student_unique : null);
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
      // Skip "-" values (placeholder for missing unique_id before first payment)
      const bodyUid = (unique_id && unique_id !== '-') ? unique_id : ((student_unique && student_unique !== '-') ? student_unique : null);
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
            const newAppRow = { student_id: debugInfo.student.id, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
            const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            if(!createErr && createdApp && createdApp.app_id){ normalizedAppId = Number(createdApp.app_id); console.log('/api/documents created admission_applications fallback', normalizedAppId); }
            else { console.log('/api/documents debug (create failed, no fallback)', { createErr: createErr ? createErr.message : null }); return res.status(400).json({ error: `Application #${candidate} not found and could not be created. Please ensure the application exists before uploading documents.`, debug: debugInfo }); }
          }catch(e){ console.warn('create admission_applications exception', e); return res.status(400).json({ error: `Application #${candidate} not found. Please complete the enquiry or ensure the application exists.` }); }
        } else {
          // No student known and app_id doesn't exist: return error
          console.log('/api/documents debug (app_id not found, no student)', { candidate, provided_app_id: app_id });
          return res.status(400).json({ error: `Application #${candidate} not found. Please ensure the application exists before uploading documents.`, debug: debugInfo });
        }
      }
    }

    // Check if app_id is in "BE-{student_id}" format (Basic Entry) before trying to use it directly
    if(!normalizedAppId && app_id && String(app_id).startsWith('BE-')){
      try{
        const beStudentId = Number(String(app_id).substring(3));
        if(!isNaN(beStudentId)){
          // Try to get or create admission_applications for this basic entry student
          const { data: beStudent, error: beErr } = await supabase.from('students').select('id').eq('id', beStudentId).maybeSingle();
          if(!beErr && beStudent && beStudent.id){
            // Create admission_applications for this basic entry student if it doesn't exist
            const { data: existingApp, error: checkErr } = await supabase.from('admission_applications').select('app_id').eq('student_id', beStudent.id).maybeSingle();
            if(!checkErr && existingApp && existingApp.app_id){
              normalizedAppId = Number(existingApp.app_id);
              console.log('/api/documents found existing admission_applications for BE student', normalizedAppId);
            } else {
              const newAppRow = { student_id: beStudent.id, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
              const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
              if(!createErr && createdApp && createdApp.app_id){ normalizedAppId = Number(createdApp.app_id); console.log('/api/documents created admission_applications for BE student', normalizedAppId); }
            }
          }
        }
      }catch(e){ console.warn('BE app_id resolution failed', e); }
    }

    if(!normalizedAppId){ console.log('/api/documents debug (still no normalizedAppId)', debugInfo); return res.status(400).json({ error: 'Could not determine application ID. Please ensure the application exists or use format "BE-{student_id}" for Basic Entry students.', debug: debugInfo }); }

    const row = { app_id: Number(normalizedAppId), document_type: document_type || null, document_url, file_size: file_size ? Number(file_size) : null, uploaded_by: uploaded_by ? Number(uploaded_by) : null, bill_number: bill_number || null };
    let insertAttempt = 0;
    while(true){
      insertAttempt++;
      const { data, error } = await supabase.from('documents').insert(row).select().maybeSingle();
      if(!error){
        // If a bill_number was provided, persist it to the admission_applications table
        if(row.bill_number){
          try{
            await supabase.from('admission_applications').update({ bill_number: row.bill_number }).eq('app_id', Number(normalizedAppId));
          }catch(e){ console.warn('failed to persist bill_number to admission_applications', e); }
        }
        return res.json({ ok: true, document: data }); }
      // If FK error and we have student info, attempt to create a minimal admission_applications record and retry once
      const msg = error && (error.message || String(error));
      console.error('insert document error', msg);
      if(insertAttempt === 1 && msg && msg.includes('violates foreign key') && debugInfo && debugInfo.student && debugInfo.student.id){
        try{
          console.log('/api/documents attempting to create admission_applications fallback for student', debugInfo.student.id);
            const newAppRow = { student_id: debugInfo.student.id, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
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
  }catch(e){
    const errMsg = e && e.message ? e.message : String(e);
    console.error('/api/documents exception', { error: errMsg, stack: e && e.stack });
    return res.status(500).json({ error: `Server error: ${errMsg}` });
  }
});

// Server-side upload endpoint: accepts a single file and uploads to Supabase storage using service key
app.post('/api/upload-file', uploadMemory.any(), async (req, res) => {
  try{
    const files = req.files || [];
    const { app_id, application_number, unique_id, student_unique, document_type, student_name, uploaded_by, bill_number } = req.body || {};
    console.log('/api/upload-file payload', { app_id, unique_id, student_unique, document_type, student_name, uploaded_by, bill_number, files: files.map(f=>({ field: f.fieldname, originalname: f.originalname, size: f.size })) });
    if(!files || files.length === 0) return res.status(400).json({ error: 'one or more files are required' });

    // determine app_id if unique_id or student_unique provided
    let targetAppId = null;
    // Skip "-" values (placeholder for missing unique_id before first payment)
    const uidToUse = (unique_id && unique_id !== '-') ? unique_id : ((student_unique && student_unique !== '-') ? student_unique : null);
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
            const newAppRow = { student_id: s2.id, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
            const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            if(!createErr && createdApp && createdApp.app_id){ targetAppId = Number(createdApp.app_id); console.log('/api/upload-file created admission_applications', targetAppId); }
          }catch(e){ console.warn('create admission_applications exception', e); }
        }
      } else {
        // App doesn't exist and no student info to create it - this is an error
        console.log('/api/upload-file error: app_id not found and cannot create', { app_id: candidate, uidToUse });
        return res.status(400).json({ error: `Application #${candidate} not found. Please ensure the application exists before uploading documents.` });
      }
    }
    // If still not resolved, and caller provided an application_number, try to resolve it
    if(!targetAppId && application_number){
      try{
        const { data: byNum, error: byNumErr } = await supabase.from('admission_applications').select('app_id').eq('application_number', String(application_number)).maybeSingle();
        if(!byNumErr && byNum && byNum.app_id) targetAppId = Number(byNum.app_id);
      }catch(e){ console.warn('lookup admission_applications by application_number failed (upload-file)', e); }
    }

    // If still not resolved, check if app_id is in "BE-{student_id}" format (Basic Entry)
    if(!targetAppId && app_id && String(app_id).startsWith('BE-')){
      try{
        const beStudentId = Number(String(app_id).substring(3));
        if(!isNaN(beStudentId)){
          // Try to get or create admission_applications for this basic entry student
          const { data: beStudent, error: beErr } = await supabase.from('students').select('id').eq('id', beStudentId).maybeSingle();
          if(!beErr && beStudent && beStudent.id){
            // Create admission_applications for this basic entry student
            const newAppRow = { student_id: beStudent.id, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
            const { data: createdApp, error: createErr } = await supabase.from('admission_applications').insert(newAppRow).select().maybeSingle();
            if(!createErr && createdApp && createdApp.app_id){ targetAppId = Number(createdApp.app_id); console.log('/api/upload-file resolved BE app_id to admission_applications', targetAppId); }
            else { console.log('/api/upload-file could not create admission_applications for BE student'); }
          }
        }
      }catch(e){ console.warn('BE app_id resolution failed', e); }
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
      console.log('/api/upload-file uploading to storage', { remotePath, fileSize: file.size, mimeType: file.mimetype });
      const { data: upData, error: upErr } = await supabase.storage.from('Student_files').upload(remotePath, file.buffer, { contentType: file.mimetype, upsert: false });
      if(upErr){
        const errMsg = upErr.message || String(upErr);
        console.error('/api/upload-file storage upload error', { remotePath, error: errMsg });
        return res.status(500).json({ error: `Storage upload failed: ${errMsg}` });
      }

      // construct public url
      const publicUrl = `${SUPABASE_URL.replace(/\/$/,'')}/storage/v1/object/public/Student_files/${encodeURIComponent(upData.path)}`;

      // insert metadata into documents table
      const row = { app_id: Number(targetAppId), document_type: docType || null, document_url: publicUrl, file_size: file.size ? Number(file.size) : null, uploaded_by: uploaded_by ? Number(uploaded_by) : null, bill_number: bill_number || null };
      let insertAttempt = 0;
      while(true){
        insertAttempt++;
        const { data: docData, error: docErr } = await supabase.from('documents').insert(row).select().maybeSingle();
        if(!docErr){
          // persist bill_number into admission_applications if provided
          if(row.bill_number){
            try{
              await supabase.from('admission_applications').update({ bill_number: row.bill_number }).eq('app_id', Number(targetAppId));
            }catch(e){ console.warn('failed to persist bill_number to admission_applications (upload-file)', e); }
          }
          results.push({ ok: true, document: docData, publicUrl }); break; }
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
              const newAppRow = { student_id: fallbackStudentId, status: 'created', processed_by: null, processed_at: null, application_number: application_number || null };
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

    // For single file upload, return at top level; for multiple, include results array for compatibility
    if(results.length === 1 && results[0].ok === true){
      // Return first successful result's properties at top level
      const { ok, document, publicUrl } = results[0];
      return res.json({ ok: true, document, publicUrl });
    }
    // Multiple files or mixed results: return full results array
    return res.json({ ok: true, results });
  }catch(e){
    const errMsg = e && e.message ? e.message : String(e);
    console.error('/api/upload-file exception', { error: errMsg, stack: e && e.stack });
    return res.status(500).json({ error: `Server error: ${errMsg}` });
  }
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

// Create admission_application for a student (used by direct entry flow)
app.post('/api/admission_applications', async (req, res) => {
  try{
    const { student_id } = req.body || {};
    if(!student_id) return res.status(400).json({ ok:false, error: 'student_id is required' });
    const row = { student_id: Number(student_id), status: 'created' };
    const { data, error } = await supabase.from('admission_applications').insert(row).select().maybeSingle();
    if(error) return res.status(500).json({ ok:false, error: error.message });
    return res.json({ ok:true, item: data });
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// ── Basic Enquiry endpoints ──────────────────────────────────────────────────

// List — by default only returns records not yet added to a full enquiry.
// Pass ?all=1 to include already-added ones (used by the Fetch modal).
app.get('/api/basic_enquiry', async (req, res) => {
  try{
    const showAll = req.query.all === '1';
    let q = supabase.from('basic_enquiry').select('*').order('created_at', { ascending: false });
    if(!showAll) q = q.eq('added_to_enquiry', false);
    const { data, error } = await q.limit(2000);
    if(error) return res.status(500).json({ error: error.message });
    res.json(data || []);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Get single record by id
app.get('/api/basic_enquiry/:id', async (req, res) => {
  try{
    const { data, error } = await supabase.from('basic_enquiry').select('*').eq('id', req.params.id).maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    if(!data) return res.status(404).json({ error: 'Not found' });
    res.json(data);
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Create new basic enquiry record + also create student record for payment collection
app.post('/api/basic_enquiry', async (req, res) => {
  try{
    const { full_name, gender, whatsapp_number, date_of_birth, mother_tongue,
            father_name, father_phone, mother_name, mother_phone,
            school_10_name, school_10_place, school_12_name, school_12_place,
            reference_type, reference_name, date } = req.body || {};
    if(!full_name) return res.status(400).json({ error: 'full_name is required' });
    
    // 1. Create student record in students table (so they appear in payment page)
    const studentRecord = {
      full_name,
      phone: whatsapp_number || null,
      whatsapp_number: whatsapp_number || null,
      gender: gender || null,
      date_of_birth: date_of_birth || null,
      mother_tongue: mother_tongue || null,
      father_name: father_name || null,
      father_phone: father_phone || null,
      mother_name: mother_name || null,
      mother_phone: mother_phone || null,
      reference_details: reference_name || null,
    };
    const { data: createdStudent, error: studentErr } = await supabase.from('students').insert(studentRecord).select().maybeSingle();
    if(studentErr) return res.status(500).json({ error: 'Failed to create student: ' + studentErr.message });
    const studentId = createdStudent && createdStudent.id;
    
    // 2. Create basic enquiry record
    const beRow = {
      full_name,
      gender: gender || null,
      whatsapp_number: whatsapp_number || null,
      date_of_birth: date_of_birth || null,
      mother_tongue: mother_tongue || null,
      father_name: father_name || null,
      father_phone: father_phone || null,
      mother_name: mother_name || null,
      mother_phone: mother_phone || null,
      school_10_name: school_10_name || null,
      school_10_place: school_10_place || null,
      school_12_name: school_12_name || null,
      school_12_place: school_12_place || null,
      reference_type: reference_type || null,
      reference_name: reference_name || null,
      student_id: studentId,
    };
    if(date) beRow.date = date;
    const { data: beData, error: beError } = await supabase.from('basic_enquiry').insert(beRow).select().maybeSingle();
    if(beError) return res.status(500).json({ error: beError.message });
    
    res.json({ ok: true, item: beData, student_id: studentId });
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Mark a basic enquiry record as added to full enquiry
app.put('/api/basic_enquiry/:id/mark_added', async (req, res) => {
  try{
    const { data, error } = await supabase.from('basic_enquiry')
      .update({ added_to_enquiry: true })
      .eq('id', req.params.id)
      .select().maybeSingle();
    if(error) return res.status(500).json({ error: error.message });
    res.json({ ok: true, item: data });
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// Delete a basic enquiry record and its linked student (if any)
app.delete('/api/basic_enquiry/:id', async (req, res) => {
  try{
    const id = req.params.id;
    // fetch the basic_enquiry row to check for linked student
    const { data: beRec, error: selErr } = await supabase.from('basic_enquiry').select('id,student_id').eq('id', id).maybeSingle();
    if(selErr) return res.status(500).json({ error: selErr.message });

    // delete the basic_enquiry row
    const { error: delErr } = await supabase.from('basic_enquiry').delete().eq('id', id);
    if(delErr) return res.status(500).json({ error: delErr.message });

    // if a linked student exists, attempt to delete that student as well
    if(beRec && beRec.student_id){
      try{
        const { error: delStuErr } = await supabase.from('students').delete().eq('id', beRec.student_id);
        if(delStuErr) console.warn('Failed to delete linked student', delStuErr.message || delStuErr);
      }catch(e){ console.warn('Exception deleting linked student', e); }
    }

    res.json({ ok: true });
  }catch(e){ res.status(500).json({ error: String(e) }); }
});

// ── End Basic Enquiry endpoints ──────────────────────────────────────────────

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

// Payments: auto-generate next bill number
app.get('/api/payments/next_bill', async (req, res) => {
  try{
    const year = new Date().getFullYear();
    const prefix = `BILL-${year}-`;
    const { data, error } = await supabase.from('payments').select('bill_no').ilike('bill_no', `${prefix}%`).order('bill_no', { ascending: false }).limit(1);
    if(error) return res.status(500).json({ ok:false, error: error.message });
    let nextNum = 1;
    if(data && data.length > 0 && data[0].bill_no){
      const parts = data[0].bill_no.split('-');
      const last = parseInt(parts[parts.length-1], 10);
      if(!isNaN(last)) nextNum = last + 1;
    }
    const bill_no = prefix + String(nextNum).padStart(3, '0');
    return res.json({ ok:true, bill_no });
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
        unique_id: stu ? (stu.uniq_id || stu.unique_id) : p.unique_id || null,
        community: stu ? (stu.community || p.community || null) : p.community || null
      });
    });

    return res.json(out);
  }catch(e){ return res.status(500).json({ ok:false, error: String(e) }); }
});

// Payment candidates: apps that appear in counselling_records OR documents but are not present in payments
app.get('/api/payment_candidates', async (req, res) => {
  try{
    let output = [];

    // ─────────────────────────────────────────
    // PART 1: Existing flow (enquiry/counselling students)
    // ─────────────────────────────────────────
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
    (paidApps||[]).map(String).forEach(x => all.delete(x));

    const appIds = Array.from(all).map(x => Number(x)).filter(x => !isNaN(x));
    
    if(appIds.length > 0){
      const { data: apps, error: appsErr } = await supabase.from('admission_applications').select('*').in('app_id', appIds);
      if(appsErr) console.warn('admission_applications lookup error', appsErr);
      else if(Array.isArray(apps)){
        let studentIds = apps.filter(a=>a && a.student_id).map(a => a.student_id);
        const appsMissingStudent = apps.filter(a => !(a && a.student_id)).map(a => a.app_id).filter(Boolean);
        if(appsMissingStudent.length > 0){
          try{
            const { data: crs, error: crErr } = await supabase.from('counselling_records').select('app_id,student_id').in('app_id', appsMissingStudent);
            if(crErr) console.warn('counselling_records lookup for missing student_ids failed', crErr.message);
            if(Array.isArray(crs)) crs.forEach(r => { if(r && r.student_id) studentIds.push(r.student_id); });
          }catch(e){ console.warn('counselling_records extra lookup exception', e); }
        }

        let counsellingMap = {};
        try{
          const { data: crAll, error: crAllErr } = await supabase.from('counselling_records').select('app_id,allotted_dept_id,quota_type').in('app_id', appIds);
          if(crAllErr) console.warn('counselling_records allotment lookuperror', crAllErr.message);
          if(Array.isArray(crAll)) crAll.forEach(r => { if(r && r.app_id) counsellingMap[String(r.app_id)] = r; });
        }catch(e){ console.warn('counselling_records allotment lookup exception', e); }

        studentIds = Array.from(new Set(studentIds.map(x => Number(x)).filter(x => !isNaN(x))));
        let students = [];
        if(studentIds.length > 0){
          const { data: studs, error: studsErr } = await supabase.from('students').select('*').in('id', studentIds);
          if(studsErr) console.warn('students lookup error', studsErr);
          if(Array.isArray(studs)){
            students = studs.map(s => {
              const display_name = s.full_name || s.student_name || s.name || s.fullname || ((s.first_name||'') + (s.last_name ? ' ' + s.last_name : '')) || null;
              const uniq = s.unique_id || s.uniqueId || s.registration_id || s.registration_no || null;
              return Object.assign({}, s, { display_name, uniq_id: uniq });
            });
          } else students = [];
        }

        const studentMap = {};
        (students||[]).forEach(s => { if(s && s.id) studentMap[String(s.id)] = s; });

        apps.forEach(a => {
          const stu = a && (a.student_id || a.student) ? studentMap[String(a.student_id)] : null;
          const registration_id = a.registration_id || a.reg_id || a.registration_no || null;
          const cr = counsellingMap[String(a.app_id)];
          const preferred_dept_id = (cr && cr.allotted_dept_id) ? cr.allotted_dept_id : (a.preferred_dept_id || a.allotted_dept_id || a.preferred_branch_id || a.dept_id || null);
          const quota_type = (cr && cr.quota_type) ? cr.quota_type : (a.quota_type || a.quota || null);
          output.push({
            app_id: a.app_id,
            student_id: a.student_id || null,
            student_name: stu ? (stu.display_name || stu.full_name || stu.student_name || stu.name || null) : null,
            unique_id: stu ? (stu.uniq_id || stu.unique_id || null) : null,
            registration_id: registration_id,
            preferred_dept_id: preferred_dept_id,
            quota_type: quota_type
          });
        });
      }
    }

    // ─────────────────────────────────────────
    // PART 2: Basic entry students (NEW)
    // ─────────────────────────────────────────
    // Fetch students from basic_enquiry who don't have a payment yet
    try{
      // Get student_ids from basic_enquiry
      const { data: beData, error: beErr } = await supabase.from('basic_enquiry')
        .select('student_id')
        .not('student_id', 'is', null)
        .distinct('student_id');
      
      if(beErr) console.warn('basic_enquiry lookup error', beErr.message);
      else if(Array.isArray(beData) && beData.length > 0){
        const beStudentIds = beData.map(r => r.student_id).filter(id => id);
        
        // Remove student_ids that already have payments
        const { data: payStudents, error: payStErr } = await supabase.from('payments').select('student_id').in('student_id', beStudentIds);
        if(payStErr) console.warn('payments by student lookup error', payStErr.message);
        
        const paidStudentIds = new Set((Array.isArray(payStudents) ? payStudents.map(p => p.student_id).filter(Boolean) : []).map(x => Number(x)));
        const candidateIds = beStudentIds.filter(id => !paidStudentIds.has(Number(id)));

        if(candidateIds.length > 0){
          const { data: candidates, error: candErr } = await supabase.from('students').select('*').in('id', candidateIds);
          if(candErr) console.warn('basic entry students lookup error', candErr.message);
          else if(Array.isArray(candidates)){
            candidates.forEach(s => {
              const display_name = s.full_name || s.student_name || s.name || s.fullname || ((s.first_name||'') + (s.last_name ? ' ' + s.last_name : '')) || null;
              const uniq = s.unique_id || s.uniqueId || s.registration_id || s.registration_no || null;
              // For basic entry students, use student.id as app_id if they don't have one
              const appId = s.app_id || `BE-${s.id}`;
              output.push({
                app_id: appId,
                student_id: s.id,
                student_name: display_name,
                unique_id: uniq,
                registration_id: s.registration_id || s.reg_id || s.registration_no || null,
                preferred_dept_id: null,
                quota_type: null,
                is_basic_entry: true
              });
            });
          }
        }
      }
    }catch(e){ console.warn('basic_enquiry candidates error', e); }

    // Remove duplicates by app_id
    const seen = new Set();
    output = output.filter(item => {
      const key = String(item.app_id);
      if(seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    return res.json(output);
  }catch(e){ console.error('payment_candidates error', e && e.stack ? e.stack : e); return res.status(500).json({ ok:false, error: String(e) }); }
});

// Create a payment record
app.post('/api/payments', async (req, res) => {
  try{
    const body = req.body || {};
    const app_id = body.app_id || body.appId || null;
    const bill_no = body.bill_no || body.billNo || null;
    const mode_of_payment = body.mode_of_payment || body.mode || null;
    const amount = (body.amount !== undefined && body.amount !== null) ? Number(body.amount) : null;
    // new fields
    const payment_type = body.payment_type || null;
    const reference_number = body.reference_number || body.upi_id || body.upiId || null;
    const payment_date = body.payment_date || new Date().toISOString().slice(0,10);
    const branch_name = body.branch_name || null;
    // student identity
    let student_id = body.student_id ? Number(body.student_id) : null;

    if(!bill_no) return res.status(400).json({ ok:false, error: 'bill_no is required' });
    if(!mode_of_payment) return res.status(400).json({ ok:false, error: 'mode_of_payment is required' });
    if(amount === null || isNaN(amount)) return res.status(400).json({ ok:false, error: 'amount is required and must be numeric' });

    // Resolve student_id from app_id if provided and student_id missing
    if(app_id && !student_id){
      const { data: appRow, error: appErr } = await supabase.from('admission_applications').select('app_id,student_id').eq('app_id', Number(app_id)).maybeSingle();
      if(appErr) return res.status(500).json({ ok:false, error: appErr.message });
      if(appRow && appRow.student_id) student_id = Number(appRow.student_id);
    }

    // Resolve student_id from unique_id if still missing
    if(!student_id && body.unique_id){
      const { data: stuRow, error: stuErr } = await supabase.from('students').select('id').eq('unique_id', String(body.unique_id)).maybeSingle();
      if(stuErr) return res.status(500).json({ ok:false, error: stuErr.message });
      if(stuRow && stuRow.id) student_id = Number(stuRow.id);
    }

    if(!student_id) return res.status(400).json({ ok:false, error: 'Cannot determine student_id. Provide student_id, unique_id, or app_id.' });

    const row = {
      student_id,
      bill_no: String(bill_no),
      mode_of_payment: String(mode_of_payment),
      amount: Number(amount),
      payment_date,
      created_at: payment_date,
    };
    if(app_id) row.app_id = Number(app_id);
    if(payment_type) row.payment_type = String(payment_type);
    if(reference_number) row.reference_number = String(reference_number);
    if(branch_name) row.branch_name = String(branch_name);

    const { data: inserted, error: insErr } = await supabase.from('payments').insert(row).select().maybeSingle();
    if(insErr) return res.status(500).json({ ok:false, error: insErr.message });

    // ── First-payment logic: generate unique ID + send welcome email ──────────
    let generatedUniqueId = null;
    try{
      // Check if any previous payments exist for this student (excluding the one just inserted)
      const { data: prevPays } = await supabase.from('payments')
        .select('id').eq('student_id', student_id).neq('id', inserted.id).limit(1);
      const isFirstPayment = !prevPays || prevPays.length === 0;

      if(isFirstPayment){
        generatedUniqueId = await generateUniqueStudentId();
        // Update students table with the new unique_id
        await supabase.from('students').update({ unique_id: generatedUniqueId }).eq('id', student_id);
        // Update enquiries table for this student
        await supabase.from('enquiries').update({ unique_id: generatedUniqueId }).eq('student_id', student_id);
        console.log('[Payment] First payment — unique_id generated:', generatedUniqueId, 'for student_id:', student_id);

        // Send welcome email asynchronously
        (async () => {
          try{
            const brevoKey = (process.env.BREVO_API_KEY || '').trim();
            const smtpUser = (process.env.SMTP_USER || '').trim();
            if(!brevoKey && !smtpUser){ console.warn('[Email] No provider configured; skipping first-payment email'); return; }
            const fromName = process.env.COLLEGE_NAME || smtpUser || 'Admissions';
            // Load full student data for email template
            const { data: stu } = await supabase.from('students').select('*').eq('id', student_id).maybeSingle();
            if(!stu) return;
            const toEmail = stu.email || stu.contact_email || null;
            if(!toEmail){ console.warn('[Email] No email on student', student_id, '— skipping first-payment email'); return; }
            const tplData = Object.assign({}, stu, { unique_id: generatedUniqueId, college_name: process.env.COLLEGE_NAME || '' });
            if(!tplData.phone || typeof tplData.phone === 'boolean') tplData.phone = tplData.whatsapp_number || '';
            function renderTemplate(tpl, data){
              if(!tpl || typeof tpl !== 'string') return '';
              return tpl.replace(/\{\{\s*([a-zA-Z0-9_]+)(?:\s+or\s+'([^']*)')?\s*\}\}/g, (m, key, fallback) => {
                const val = data && (key in data) ? data[key] : undefined;
                if(val === undefined || val === null || val === '') return (fallback !== undefined ? fallback : '');
                return String(val);
              }).replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, key) => {
                const val = data && (key in data) ? data[key] : '';
                return (val === undefined || val === null) ? '' : String(val);
              });
            }
            let htmlTpl = null, textTpl = null;
            try{
              const hp = path.join(__dirname, 'templates', 'emails', 'enquiry.html');
              const tp = path.join(__dirname, 'templates', 'emails', 'enquiry.txt');
              if(fs.existsSync(hp)) htmlTpl = fs.readFileSync(hp, 'utf8');
              if(fs.existsSync(tp)) textTpl = fs.readFileSync(tp, 'utf8');
            }catch(e){ console.warn('email template read error', e); }
            const htmlBody = renderTemplate(htmlTpl || '', tplData);
            const textBody = renderTemplate(textTpl || '', tplData) || (htmlBody ? htmlBody.replace(/<[^>]+>/g, '') : '');
            const subject = `${tplData.college_name || 'Admissions'} - Welcome! Your Unique ID: ${generatedUniqueId}`;
            await sendEmail({ from: smtpUser, fromName, to: toEmail, subject, text: textBody, html: htmlBody });
            console.log('[Payment] Welcome email sent to', toEmail, 'unique_id:', generatedUniqueId);
          }catch(e){ console.warn('[Payment] Welcome email error', e && e.message ? e.message : e); }
        })();
      }
    }catch(e){ console.warn('[Payment] first-payment unique_id error', e && e.message ? e.message : e); }
    // ─────────────────────────────────────────────────────────────────────────

    return res.json({ ok:true, payment: inserted, unique_id: generatedUniqueId });
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

    // fetch application_number for the target apps so client can display application_number instead of numeric id
    const { data: appsInfo, error: appsErr } = await supabase.from('admission_applications').select('app_id,application_number').in('app_id', targetAppIds);
    if(appsErr) return res.status(500).json({ error: appsErr.message });
    const appNumMap = {};
    (appsInfo || []).forEach(a => { appNumMap[a.app_id] = a.application_number || null; });

    const { data, error } = await supabase.from('documents').select('*').in('app_id', targetAppIds).order('created_at', { ascending: false }).limit(500);
    if(error) return res.status(500).json({ error: error.message });
    // attach application_number to each document row for convenience
    const out = (data || []).map(d => Object.assign({}, d, { application_number: appNumMap[d.app_id] || null }));
    res.json(out);
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

// Return latest bill_number per app_id for given comma-separated app_ids
app.get('/api/documents/bills', async (req, res) => {
  try{
    const appsParam = req.query.app_ids || req.query.appIds || req.query.apps;
    if(!appsParam) return res.status(400).json({ error: 'app_ids query parameter required (comma separated)' });
    const appList = appsParam.split(',').map(s => Number(s.trim())).filter(n => !isNaN(n));
    if(appList.length === 0) return res.status(400).json({ error: 'no valid app_ids provided' });

    // First, try to read bill_number from admission_applications (preferred source)
    const { data: appsData, error: appsErr } = await supabase.from('admission_applications').select('app_id,bill_number').in('app_id', appList);
    if(appsErr) return res.status(500).json({ error: appsErr.message });
    const mapping = {};
    (appsData || []).forEach(a => { mapping[a.app_id] = a.bill_number || null; });

    // For any app_id that still has null/undefined bill_number, fall back to recent documents
    const missing = appList.filter(id => mapping[id] === null || mapping[id] === undefined);
    if(missing.length > 0){
      const { data: docsData, error: docsErr } = await supabase.from('documents').select('app_id,bill_number,created_at').in('app_id', missing).order('created_at', { ascending: false }).limit(2000);
        if(docsErr) return res.status(500).json({ error: docsErr.message });
        (docsData || []).forEach(d => { if(mapping[d.app_id] === undefined || mapping[d.app_id] === null) mapping[d.app_id] = d.bill_number || null; });
    }
    return res.json(mapping);
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

// Lightweight health-check used by the self-ping keep-alive
app.get('/health', (req, res) => res.json({ ok: true, ts: Date.now() }));

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server listening on http://localhost:${port}`);

  // Self-ping to prevent Render free-tier from sleeping after 15 min of inactivity.
  // Pings every 10 minutes so Render never sees a 15-min silence window.
  const SELF_URL = process.env.RENDER_EXTERNAL_URL;
  if (SELF_URL) {
    const https = require('https');
    setInterval(() => {
      https.get(SELF_URL + '/health', (res) => {
        console.log(`[keep-alive] ping → ${res.statusCode}`);
      }).on('error', (err) => {
        console.warn('[keep-alive] ping failed:', err.message);
      });
    }, 10 * 60 * 1000); // every 10 minutes
  }
});
