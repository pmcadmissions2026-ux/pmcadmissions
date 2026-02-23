// Minimal Supabase REST helper for client-side pages
(function(){
    const SUPABASE_URL = 'https://izxxhnrkcsnnabdhvixh.supabase.co';
    const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6eHhobnJrY3NubmFiZGh2aXhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1NzkzMDYsImV4cCI6MjA4NTE1NTMwNn0.mVPXk2XF9DzGsZo_SJuTHcXPArdWywxLWJZw3DD9gkE';

    function log(){ if(window.console) console.log.apply(console, arguments); }

    async function fetchTable(table, opts={}){
        const url = `${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/${table}?select=*` + (opts.query?('&'+opts.query):'');
        const res = await fetch(url, { headers: { apikey: ANON_KEY, Authorization: `Bearer ${ANON_KEY}` } });
        if(!res.ok) throw new Error('fetch error: ' + res.status);
        return res.json();
    }

    async function postRow(table, row){
        const url = `${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/${table}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type':'application/json', apikey: ANON_KEY, Authorization: `Bearer ${ANON_KEY}` },
            body: JSON.stringify(row)
        });
        if(!res.ok) throw new Error('post error: ' + res.status + ' ' + await res.text());
        return res.json();
    }

    // Render helpers: fill a tbody element with rows for common shapes
    function renderTable(tbody, rows){
        if(!tbody) return;
        tbody.innerHTML = '';
        rows.forEach(r=>{
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-[#f9fafb] dark:hover:bg-[#111827] transition-colors';
            // naive: render each value in a cell
            for(const k in r){
                const td = document.createElement('td');
                td.className = 'px-6 py-4 whitespace-nowrap text-sm text-[#617589] dark:text-[#a0aec0]';
                td.textContent = (r[k] === null || r[k] === undefined) ? '' : String(r[k]);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        });
    }

    // Auto-load any tbody elements that declare a `data-table` attribute.
    // This avoids guessing table names from the URL (which caused 404s).
    async function autoLoadForPage(){
        const tbodies = Array.from(document.querySelectorAll('tbody[data-table]'));
        if(tbodies.length === 0) return;
        await Promise.all(tbodies.map(async (tbody) => {
            const tableName = tbody.getAttribute('data-table');
            if(!tableName) return;
            try{
                const rows = await fetchTable(tableName, {query: 'limit=100'});
                renderTable(tbody, rows);
                log('supabase_client: loaded', tableName, rows.length);
            }catch(e){ log('supabase_client error', e.message); }
        }));
    }

    window.SupabaseClient = {
        fetchTable, postRow, renderTable, autoLoadForPage
    };

    // expose a small helper on DOM ready
    document.addEventListener('DOMContentLoaded', ()=>{
        try{ const page = (document.body && document.body.dataset && document.body.dataset.page) ? document.body.dataset.page : null; autoLoadForPage(page); }catch(e){}
    });

})();
