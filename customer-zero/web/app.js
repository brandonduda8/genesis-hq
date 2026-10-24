'use strict';
let csrf = null;
const $ = id => document.getElementById(id);
async function json(path, options={}) {
  const response = await fetch(path, {credentials:'same-origin',cache:'no-store', ...options});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'REQUEST_FAILED');
  return body;
}
function showLogin() {$('dashboard').hidden=true;$('login').hidden=false;csrf=null;}
function showDashboard() {$('dashboard').hidden=false;$('login').hidden=true;}
function display(id, value) {$(id).textContent = value == null ? 'UNKNOWN' : String(value);}
async function refresh() {
  try {
    const s = await json('/api/status');
    display('processState', s.host?.observation === 'LOCAL_PROCESS_MEASURED_NOW' ? 'RUNNING (MEASURED)' : 'UNKNOWN');
    display('uptime', s.host?.process?.uptime_seconds == null ? null : `${s.host.process.uptime_seconds} sec uptime`);
    display('hostCpu', s.host?.host?.logical_cpus_reported == null ? null : `${s.host.host.logical_cpus_reported} reported CPUs`);
    display('hostMem', s.host?.host?.memory_available_mib_host_estimate == null ? null : `${s.host.host.memory_available_mib_host_estimate} MiB host-estimated free`);
    display('codyStatus', s.cody?.status);
    display('providerStatus', s.provider?.status);
    $('details').textContent = JSON.stringify(s.host,null,2);
    const workers = $('workers'); workers.replaceChildren();
    if (s.worker_bridge?.lanes?.length) {
      for (const w of s.worker_bridge.lanes) {
        const span=document.createElement('span');span.className='worker';
        span.textContent=`${w.name}: ${w.bridge_reported_state} (bridge self-report only)`;
        workers.append(span);
      }
    } else workers.textContent = `No verified worker presence — bridge: ${s.worker_bridge?.status || 'UNKNOWN'}`;
  } catch(e) { if(e.message === 'LOGIN_REQUIRED') showLogin(); else $('details').textContent=`Status unavailable: ${e.message}`; }
}
$('loginForm').addEventListener('submit', async event=>{
  event.preventDefault();$('loginError').textContent='';
  const input=$('ownerToken');const token=input.value;input.value='';
  try {
    const s=await json('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({owner_token:token})});
    csrf=s.csrf_token;showDashboard();await refresh();
  } catch { $('loginError').textContent='Unable to sign in. Verify your local owner token.'; }
});
$('refresh').addEventListener('click',refresh);
$('logout').addEventListener('click',async()=>{
  try {await json('/api/logout',{method:'POST',headers:{'X-Genesis-CSRF':csrf || ''}});}catch{}
  showLogin();
});
(async()=>{try{const s=await json('/api/session');if(s.authenticated){csrf=s.csrf_token;showDashboard();await refresh();}else showLogin();}catch{showLogin();}})();