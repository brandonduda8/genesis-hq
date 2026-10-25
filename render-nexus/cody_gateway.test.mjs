import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {createCodyGateway, validatePulse} from './cody_gateway.mjs';

const owner = 'owner-' + 'o'.repeat(44);
const secret = 'cody-' + 'c'.repeat(44);
const at = new Date('2026-10-25T18:00:00Z').getTime();
const env = {NEXUS_OWNER_TOKEN: owner, NEXUS_CODY_NODE_TOKEN: secret};
const pulse = () => ({schema:'genesis-cody-standby/1',node:'cody-backup',
  boot_id:'c'.repeat(32),seq:1,observed_at:'2026-10-25T18:00:00Z',
  state:'MODEL_MISSING',capabilities:['probe','receipt'],github_https:true,model_endpoint:null});

async function makeServer(opts={}) {
  let current = opts.clockValue ?? at;
  const app = createCodyGateway({env:opts.env ?? env,clock:()=>current,
    legacyHandler:(_req,res)=>{res.writeHead(200);res.end('LEGACY')}});
  const server = http.createServer(app);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base = 'http://127.0.0.1:'+server.address().port;
  return {base,setTime:ms=>{current=ms},close:()=>new Promise(resolve=>server.close(resolve))};
}
function post(s, value=pulse(), key=secret) {
  return fetch(s.base+'/api/cody/heartbeat',{method:'POST',headers:{authorization:'Bearer '+key,
    'content-type':'application/json'},body:JSON.stringify(value)});
}
function get(s,key=owner) {
  return fetch(s.base+'/api/cody/status',{headers:{authorization:'Bearer '+key}});
}
test('disabled receiver denies pulses and status remains unknown',async()=>{
  const s=await makeServer({env:{NEXUS_OWNER_TOKEN:owner}});
  try{assert.equal((await post(s)).status,503);
    const status=await(await get(s)).json();
    assert.equal(status.presence,'RECEIVER_NOT_CONFIGURED');
    assert.equal(status.remote_execution_enabled,false);
  }finally{await s.close()}
});
test('status and heartbeat require distinct tokens',async()=>{
  const s=await makeServer();try{
    assert.equal((await fetch(s.base+'/api/cody/status')).status,401);
    assert.equal((await get(s,secret)).status,401);
    assert.equal((await post(s,pulse(),owner)).status,401);
    assert.equal((await post(s,pulse(),secret)).status,202);
  }finally{await s.close()}
});
test('valid heartbeat reports recent observation, not Cody execution',async()=>{
  const s=await makeServer();try{
    assert.equal((await post(s)).status,202);
    const status=await(await get(s)).json();
    assert.equal(status.presence,'RECENT_TOKEN_AUTHENTICATED_SELF_REPORT');
    assert.equal(status.latest.state,'MODEL_MISSING');
    assert.equal(status.model_inference_verified,false);
    assert.equal(status.remote_execution_enabled,false);
  }finally{await s.close()}
});
test('replay is idempotent only when bytes match, rejects old/conflicting seq',async()=>{
  const s=await makeServer();try{
    assert.equal((await post(s)).status,202);
    const retry=await post(s);assert.equal(retry.status,200);assert.equal((await retry.json()).duplicate,true);
    const alter=pulse();alter.state='DEGRADED';assert.equal((await post(s,alter)).status,409);
    const newer=pulse();newer.seq=2;assert.equal((await post(s,newer)).status,202);
    assert.equal((await post(s)).status,409);
  }finally{await s.close()}
});
test('expired presence reverts to stale instead of claiming online',async()=>{
  const s=await makeServer();try{
    await post(s);s.setTime(at+76*60000);
    const status=await(await get(s)).json();
    assert.equal(status.presence,'STALE_SELF_REPORT');
  }finally{await s.close()}
});
test('malformed, stale, oversized or secret-like extra data rejected',async()=>{
  const s=await makeServer();try{
    const old=pulse();old.observed_at='2026-10-24T18:00:00Z';assert.equal((await post(s,old)).status,400);
    const leaked=pulse();leaked.api_key='secret';assert.equal((await post(s,leaked)).status,400);
    const invalid=pulse();invalid.model_endpoint=true;invalid.state='MODEL_ENDPOINT_OBSERVED';invalid.capabilities=['root'];
    assert.equal((await post(s,invalid)).status,400);
    const tooLarge={...pulse(),state:'STARTING',capabilities:['probe'],padding:'x'.repeat(3000)};
    assert.equal((await post(s,tooLarge)).status,413);
  }finally{await s.close()}
});
test('unknown paths still reach old Genesis Alliance HQ',async()=>{
  const s=await makeServer();try{const r=await fetch(s.base+'/api/health');assert.equal(await r.text(),'LEGACY')}finally{await s.close()}
});
test('identical owner/node token is rejected as unsafe configuration',async()=>{
  const s=await makeServer({env:{NEXUS_OWNER_TOKEN:owner,NEXUS_CODY_NODE_TOKEN:owner}});
  try{const j=await(await get(s)).json();assert.equal(j.presence,'RECEIVER_NOT_CONFIGURED')}finally{await s.close()}
});
test('wrong types and future timestamp cannot claim readiness',()=>{
  const future=pulse();future.observed_at='2026-10-25T18:20:00Z';
  assert.throws(()=>validatePulse(future,at));
  const bogus=pulse();bogus.github_https='yes';assert.throws(()=>validatePulse(bogus,at));
  const fake=pulse();fake.state='MODEL_ENDPOINT_OBSERVED';assert.throws(()=>validatePulse(fake,at));
});
