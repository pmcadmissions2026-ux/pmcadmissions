(function(){
    // Lightweight resilient AdminAPI initializer.
    function pageLog(msg){
        try{
            const el = document.getElementById('dbg-output') || document.getElementById('page-errors-overlay');
            if(el){ if(typeof msg === 'object') msg = JSON.stringify(msg, null, 2); el.textContent += msg + '\n'; return; }
        }catch(e){}
        try{ console.log(msg); }catch(_){}
    }

    if(window.AdminAPI){ pageLog('admin_api_init: AdminAPI already present'); return; }
    pageLog('admin_api_init: installing AdminAPI fallback');

    try{
        window.ADMIN_SUPABASE_URL = window.ADMIN_SUPABASE_URL || 'https://izxxhnrkcsnnabdhvixh.supabase.co';
        window.ADMIN_SUPABASE_KEY = window.ADMIN_SUPABASE_KEY || '';
        const SUPABASE_URL = window.ADMIN_SUPABASE_URL;
        const SUPABASE_KEY = window.ADMIN_SUPABASE_KEY;
        const base = SUPABASE_URL.replace(/\/$/, '') + '/rest/v1';
        const headers = { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` };

        function buildParams(params){
            if(!params) return '';
            const qs = new URLSearchParams();
            for(const k of Object.keys(params)) qs.append(k, params[k]);
            const s = qs.toString();
            return s ? ('?' + s) : '';
        }

        async function get(table, params){
            const url = `${base}/${table}${buildParams(params)}`;
            pageLog('AdminAPI GET ' + url);
            const r = await fetch(url, { headers });
            if(!r.ok){ const t = await r.text().catch(()=>'<no-body>'); pageLog('AdminAPI GET error ' + r.status + ' ' + t); throw new Error(r.status + ' ' + t); }
            const json = await r.json();
            pageLog('AdminAPI GET success: ' + table + ' (' + (Array.isArray(json)?json.length:0) + ')');
            return json;
        }
        function list(table, limit=200){ return get(table, { select: '*', limit }); }

        window.AdminAPI = { get, list };
        pageLog('admin_api_init: AdminAPI installed');

        // Optionally populate __SERVER_DATA (non-blocking)
        (async function(){
            try{
                pageLog('admin_api_init: populateServerData start');
                const [students_sample, admissions_sample, departments_sample, academics_sample, accepted_sample] = await Promise.all([
                    window.AdminAPI.list('students', 200).catch(()=>[]),
                    window.AdminAPI.list('admissions', 200).catch(()=>[]),
                    window.AdminAPI.list('departments', 200).catch(()=>[]),
                    window.AdminAPI.list('academics', 200).catch(()=>[]),
                    window.AdminAPI.get('students', { 'select': '*', 'status': 'eq.accepted', 'limit': '200' }).catch(()=>[])
                ]);
                const studentsById = {};
                students_sample.forEach(s => { studentsById[String(s.id)] = s; });
                const deptMap = {};
                (departments_sample||[]).forEach(d => { deptMap[String(d.id)] = d; });
                const acadMap = {};
                (academics_sample||[]).forEach(a => { acadMap[String(a.student_id)] = a; });

                const assigned = (admissions_sample||[]).map(adm => {
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

                const accepted = (accepted_sample||[]).map(s => ({ student_id: s.id, name: s.full_name||s.name||'N/A', unique_id: s.unique_id, accepted_by: s.accepted_by, accepted_at: s.accepted_at, cutoff: acadMap[String(s.id)]?acadMap[String(s.id)].cutoff:null, enquiry_id:null, has_admission: (admissions_sample||[]).some(a=>String(a.student_id)===String(s.id)) }));

                const pending = (students_sample||[]).filter(s => { const sid = s.id; const hasAdm = (admissions_sample||[]).some(a=>String(a.student_id)===String(sid)); const isAccepted = (String(s.status||'').toLowerCase()==='accepted'); return !hasAdm && !isAccepted; }).map(s=>({ student_id: s.id, name: s.full_name||s.name||'N/A', unique_id: s.unique_id, community: s.community, cutoff: acadMap[String(s.id)]?acadMap[String(s.id)].cutoff:null, enquiry_id:null, time_ago:'Unknown' }));

                window.__SERVER_DATA = { pending, assigned, accepted };
                pageLog('admin_api_init: populated __SERVER_DATA — pending:' + (pending||[]).length + ' assigned:' + (assigned||[]).length + ' accepted:' + (accepted||[]).length);
            }catch(e){ pageLog('admin_api_init: populate failed: ' + (e&&e.message?e.message:String(e))); }
        })();

    }catch(e){ pageLog('admin_api_init: install failed: ' + (e&&e.message?e.message:String(e))); }
})();
