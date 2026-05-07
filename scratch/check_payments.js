const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_ANON_KEY);

async function checkPayments() {
  const { data, error } = await supabase.from('payments').select('*').limit(5);
  if (error) console.error(error);
  else console.log(JSON.stringify(data, null, 2));
}

checkPayments();
