// Minimal global debug helpers to avoid undefined onclick errors
(function(){
    function out(msg){
        try{
            const el = document.getElementById('dbg-output') || document.getElementById('page-errors-overlay');
            if(el){ if(typeof msg === 'object') msg = JSON.stringify(msg, null, 2); el.textContent += msg + "\n"; return; }
        }catch(e){}
        try{ console.log(msg); }catch(_){}
    }

    window.__dbg_manual_check = async function(){
        out('global __dbg_manual_check: invoked');
        try{
            const emailEl = document.getElementById('debug-user-email');
            const email = emailEl ? emailEl.textContent.trim() : '';
            if(window.AdminAPI && typeof window.AdminAPI.get === 'function'){
                const users = await window.AdminAPI.get('users', { select: '*', email: `eq.${email}` });
                out({ users });
                return;
            }
            out('global __dbg_manual_check: AdminAPI not available');
        }catch(e){ out('global __dbg_manual_check error: ' + (e && e.message?e.message:String(e))); }
    };

    window.__dbg_show_keys = function(){
        out('global __dbg_show_keys: ADMIN_SUPABASE_URL=' + (window.ADMIN_SUPABASE_URL||'<none>'));
        out('global __dbg_show_keys: ADMIN_SUPABASE_KEY present=' + !!window.ADMIN_SUPABASE_KEY);
        out('global __dbg_show_keys: AdminAPI present=' + !!window.AdminAPI);
    };
})();
