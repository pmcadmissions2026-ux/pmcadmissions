// Add diagnostics and export AdminAPI to window for visibility and debugging
// Proceed only if you understand security implications of exposing keys in frontend.

try {
    function pageLog(msg){
        try{
            const el = document.getElementById('dbg-output');
            if(!el) return;
            if(typeof msg === 'object') msg = JSON.stringify(msg, null, 2);
            el.textContent += msg + "\n";
        }catch(e){ /* ignore */ }
    }

    console.log('admin_api: init');
    pageLog('admin_api: init');
    window.ADMIN_SUPABASE_URL = 'https://izxxhnrkcsnnabdhvixh.supabase.co';
    // Use the anon/public key for browser requests
    window.ADMIN_SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6eHhobnJrY3NubmFiZGh2aXhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NzkzMDYsImV4cCI6MjA4NTE1NTMwNn0.mVPXk2XF9DzGsZo_SJuTHcXPArdWywxLWJZw3DD9gkE';

    const SUPABASE_URL = window.ADMIN_SUPABASE_URL;
    const SUPABASE_KEY = window.ADMIN_SUPABASE_KEY;

    window.AdminAPI = (function(){
        const base = SUPABASE_URL.replace(/\/$/, '') + '/rest/v1';
        const headers = { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` };

        function buildParams(params){
            if(!params) return '';
            const qs = new URLSearchParams();
            for(const k of Object.keys(params)){
                qs.append(k, params[k]);
            }
            const s = qs.toString();
            return s ? ('?' + s) : '';
        }

        async function get(table, params){
            const url = `${base}/${table}${buildParams(params)}`;
            console.log('AdminAPI GET', url, headers && { ok: true });
            pageLog('AdminAPI GET ' + url);
            const r = await fetch(url, { headers });
            if(!r.ok) {
                const text = await r.text().catch(()=>'<no-body>');
                const errMsg = `${r.status} ${text}`;
                console.error('AdminAPI GET error', errMsg);
                pageLog('AdminAPI GET error: ' + errMsg);
                throw new Error(errMsg);
            }
            const json = await r.json();
            pageLog('AdminAPI GET success: ' + table + ' (' + (Array.isArray(json)?json.length:0) + ')');
            return json;
        }

        async function list(table, limit=200){
            return get(table, { select: '*', limit });
        }

        return { get, list };
    })();

        (async function populateServerData(){
        try{
            console.log('admin_api: populateServerData start');
            pageLog('admin_api: populateServerData start');
            const [students_sample, admissions_sample, departments_sample, academics_sample, accepted_sample] = await Promise.all([
                window.AdminAPI.list('students', 200),
                window.AdminAPI.list('admissions', 200),
                window.AdminAPI.list('departments', 200),
                window.AdminAPI.list('academics', 200),
                window.AdminAPI.get('students', { 'select': '*', 'status': 'eq.accepted', 'limit': '200' })
            ]);

            const studentsById = {};
            students_sample.forEach(s => { studentsById[String(s.id)] = s; });
            const deptMap = {};
            (departments_sample||[]).forEach(d => { deptMap[String(d.id)] = d; });
            const acadMap = {};
            (academics_sample||[]).forEach(a => { acadMap[String(a.student_id)] = a; });

            // detect current admin identity (preserve any server-injected current_user)
            const existingCU = (window.__SERVER_DATA && window.__SERVER_DATA.current_user) || window.__CURRENT_USER || window.__USER || window.CURRENT_USER || window.USER || null;
            let adminIdent = null;
            if(existingCU){
                adminIdent = existingCU.email || existingCU.username || existingCU.id || existingCU.name || existingCU.full_name || existingCU.accepted_by || existingCU.processed_by || null;
            }

            let assigned = (admissions_sample||[]).map(adm => {
                const sid = adm.student_id;
                const stu = studentsById[String(sid)] || {};
                const prefId = adm.preferred_dept_id || adm.primary_dept_id;
                const pref = prefId != null ? deptMap[String(prefId)] : null;
                let optional = [];
                if(adm.optional_dept_ids){
                    try{ optional = typeof adm.optional_dept_ids === 'string' ? JSON.parse(adm.optional_dept_ids) : adm.optional_dept_ids; }
                    catch(e){ optional = Array.isArray(adm.optional_dept_ids)?adm.optional_dept_ids:[adm.optional_dept_ids]; }
                }
                const optional_depts = (optional||[]).map(od => deptMap[String(od)]).filter(Boolean);
                const cutoff = acadMap[String(sid)] ? acadMap[String(sid)].cutoff : null;
                return {
                    student_id: sid,
                    app_id: adm.id || adm.app_id || null,
                    name: stu.full_name || stu.name || 'N/A',
                    unique_id: stu.unique_id,
                    community: stu.community,
                    cutoff: cutoff,
                    preferred_dept: pref ? pref.dept_name : null,
                    preferred_dept_code: pref ? pref.dept_code : '',
                    optional_depts: optional_depts,
                    allotted_dept: adm.allotted_dept_id ? '-' : '-',
                    allotted_dept_code: '',
                    status: adm.status,
                    assignment_date: adm.created_at,
                    documents_uploaded: adm.documents_uploaded || false,
                    documents_count: (adm.documents && typeof adm.documents === 'object') ? Object.keys(adm.documents).length : 0,
                    documents_submitted_at: adm.documents_submitted_at || null
                };
            });

            // scope assigned admissions to current admin if we have an identity
            if(adminIdent){
                try{
                    const idLower = String(adminIdent).toLowerCase();
                    assigned = assigned.filter(a => {
                        const raw = (admissions_sample||[]).find(x => String(x.student_id) === String(a.student_id));
                        return raw && raw.processed_by && String(raw.processed_by).toLowerCase().includes(idLower);
                    });
                }catch(e){ /* ignore */ }
            }

            const accepted = (accepted_sample||[]).map(s => ({
                student_id: s.id,
                name: s.full_name || s.name || 'N/A',
                unique_id: s.unique_id,
                accepted_by: s.accepted_by,
                accepted_at: s.accepted_at,
                cutoff: acadMap[String(s.id)] ? acadMap[String(s.id)].cutoff : null,
                enquiry_id: null,
                has_admission: (admissions_sample||[]).some(a => String(a.student_id) === String(s.id))
            }));

            // scope accepted students to current admin if we have an identity
            let accepted_scoped;
            if(adminIdent){
                try{
                    const idLower = String(adminIdent).toLowerCase();
                    accepted_scoped = accepted.filter(a => {
                        const stuMatch = a.accepted_by && String(a.accepted_by).toLowerCase().includes(idLower);
                        const admMatch = (admissions_sample||[]).some(x => String(x.student_id) === String(a.student_id) && x.processed_by && String(x.processed_by).toLowerCase().includes(idLower));
                        return stuMatch || admMatch;
                    });
                }catch(e){ accepted_scoped = accepted; }
            }

            const pending = (students_sample||[]).filter(s => {
                const sid = s.id;
                const hasAdm = (admissions_sample||[]).some(a => String(a.student_id) === String(sid));
                const isAccepted = (String(s.status||'').toLowerCase() === 'accepted');
                return !hasAdm && !isAccepted;
            }).map(s => ({
                student_id: s.id,
                name: s.full_name || s.name || 'N/A',
                unique_id: s.unique_id,
                community: s.community,
                cutoff: acadMap[String(s.id)] ? acadMap[String(s.id)].cutoff : null,
                enquiry_id: null,
                time_ago: 'Unknown'
            }));

            // preserve any server-injected current_user
            const preserveCU = (window.__SERVER_DATA && window.__SERVER_DATA.current_user) ? { current_user: window.__SERVER_DATA.current_user } : {};
            const finalAccepted = (typeof accepted_scoped !== 'undefined') ? accepted_scoped : accepted;
            window.__SERVER_DATA = Object.assign({}, preserveCU, { pending, assigned, accepted: finalAccepted });
            console.log('AdminAPI populated __SERVER_DATA', window.__SERVER_DATA);
            pageLog('AdminAPI populated __SERVER_DATA — pending:' + (pending||[]).length + ' assigned:' + (assigned||[]).length + ' accepted:' + (finalAccepted||[]).length);
            try{ window.dispatchEvent(new CustomEvent('admin_api:populated', { detail: window.__SERVER_DATA })); }catch(e){}
        }catch(err){
            console.error('AdminAPI failed to populate server data', err);
            pageLog('AdminAPI failed to populate server data: ' + (err && err.message ? err.message : String(err)));
        }
    })();

    console.log('admin_api: initialized');
    pageLog('admin_api: initialized');
} catch(e) {
    console.error('admin_api: initialization error', e);
    try{ pageLog('admin_api: initialization error ' + (e && e.message ? e.message : String(e))); }catch(_){ }
}
