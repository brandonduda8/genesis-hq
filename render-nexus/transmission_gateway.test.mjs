import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createTransmissionHandler } from './transmission_gateway.mjs';
import { digest, canonical } from './transmission.mjs';

const owner='owner-'+ 'r'.repeat(45);
const env={NEXUS_OWNER_TOKEN:owner,NEXUS_GITHUB_TOKEN:'dummy-for-local-testing',NEXUS_REPO:'brandonduda8/astra-zane-bridge'};
const id='msg-'+'f'.repeat(32);
const created='2026-10-25T16:00:00Z';
const clock=()=>new Date('2026-10-25T17:00:00Z');
function data(){const envelope={schema_version:'1',message_id:id,conversation_id:'test',sender:'astra',recipient:'zane',created_at:created,msg_type:'ping',content:'hi',content_sha256:digest('hi'),attachments:[]};return {envelope,envelope_sha256:digest(canonical(envelope))}}
const wrap=x=>({content:Buffer.from(JSON.stringify(x)).toString('base64')});
function fakeFetcher({available=true,ack=true}={}){
  const record=data(),receipt={message_id:id,receiver:'zane',acked_at:'2026-10-25T16:01:00Z',envelope_sha256:record.envelope_sha256};
  return async function(url){
    if(!available)throw Error('provider connection blocked');
    const path=new URL(url).pathname;
    if(path.includes('/commits'))return Response.json([{commit:{message:`mailbox: envelope ${id} (astra->zane)`,committer:{date:'2026-10-25T16:01:00Z'}}}]);
    if(path.includes('/contents/mailbox/astra-to-zane/'))return Response.json(wrap(record));
    if(path.includes('/contents/mailbox/acks/zane/')&&ack)return Response.json(wrap(receipt));
    return Response.json({error:'not found'},{status:404});
  };
}
async function harness(opts={}){
  const handler=createTransmissionHandler({env:opts.env||env,fetcher:opts.fetcher||fakeFetcher(),clock,
    legacyHandler:(_req,res)=>{res.writeHead(200);res.end('LEGACY_OK')}});
  const server=http.createServer(handler);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  return {base,close:()=>new Promise(resolve=>server.close(resolve))};
}
const headers={authorization:'Bearer '+owner};
test('legacy gateway remains delegated intact',async()=>{const s=await harness();try{assert.equal(await(await fetch(s.base+'/api/health')).text(),'LEGACY_OK')}finally{await s.close()}});
test('mobile dashboard JS and CSS are served',async()=>{const s=await harness();try{for(const path of ['/transmission','/transmission.js','/transmission.css']){const r=await fetch(s.base+path);assert.equal(r.status,200,path);assert.ok((await r.text()).length>300)}}finally{await s.close()}});
test('all intelligence endpoints reject unauthenticated access',async()=>{const s=await harness();try{for(const path of ['/api/transmission/summary','/api/transmission/delivery?route=astra-to-zane&id='+id,'/api/transmission/events']){const r=await fetch(s.base+path);assert.equal(r.status,401,path)}}finally{await s.close()}});
test('message planning never executes commands',async()=>{const s=await harness();try{const r=await fetch(s.base+'/api/transmission/plan',{method:'POST',headers:{...headers,'content-type':'application/json'},body:JSON.stringify({content:'Investigate the provider proxy'})});assert.equal(r.status,200);const j=await r.json();assert.equal(j.gate,'BLOCKED_EGRESS');assert.equal(j.autonomous_dispatch,false)}finally{await s.close()}});
test('summary records real GitHub metadata but zero live agents',async()=>{const s=await harness();try{const r=await fetch(s.base+'/api/transmission/summary',{headers});assert.equal(r.status,200);const j=await r.json();assert.equal(j.transport,'GITHUB_REACHABLE_FROM_RENDER_ONLY');assert.ok(j.route_observations[0].last_commit_at);assert.equal(j.verified_live_agents.length,0)}finally{await s.close()}});
test('matching ACK reports transport-only, not cryptographic identity',async()=>{const s=await harness();try{const r=await fetch(s.base+'/api/transmission/delivery?route=astra-to-zane&id='+id,{headers});assert.equal(r.status,200);const j=await r.json();assert.equal(j.state,'TRANSPORT_ACK_PRESENT_IDENTITY_UNVERIFIED');assert.equal(j.authenticated,false)}finally{await s.close()}});
test('missing ack does not invent delivery',async()=>{const s=await harness({fetcher:fakeFetcher({ack:false})});try{const r=await fetch(s.base+'/api/transmission/delivery?route=astra-to-zane&id='+id,{headers});assert.equal((await r.json()).state,'PUBLISHED_NO_ACK')}finally{await s.close()}});
test('provider outage is detected as unavailable, not a verified response',async()=>{const s=await harness({fetcher:fakeFetcher({available:false})});try{const r=await fetch(s.base+'/api/transmission/summary',{headers});assert.equal((await r.json()).transport,'GITHUB_UNREACHABLE_FROM_RENDER')}finally{await s.close()}});
test('no GitHub credential is not misclassified as network outage',async()=>{const s=await harness({env:{NEXUS_OWNER_TOKEN:owner}});try{const r=await fetch(s.base+'/api/transmission/summary',{headers});assert.equal((await r.json()).transport,'GITHUB_NOT_CONFIGURED')}finally{await s.close()}});
test('invalid delivery path cannot escape fixed mailbox routes',async()=>{const s=await harness();try{const r=await fetch(s.base+'/api/transmission/delivery?route=../../evil&id='+id,{headers});assert.equal(r.status,400)}finally{await s.close()}});
test('two-vantage comparison uses local data only',async()=>{const s=await harness();try{const r=await fetch(s.base+'/api/transmission/compare',{method:'POST',headers:{...headers,'content-type':'application/json'},body:JSON.stringify({reports:[{network_group:'zane',timestamp_utc:'2026-10-25T16:55:00Z',https_ok:false},{network_group:'phone',timestamp_utc:'2026-10-25T16:56:00Z',https_ok:true}]})});assert.equal((await r.json()).classification,'NETWORK_PATH_DIFFERENCE')}finally{await s.close()}});
test('SSE emits server observations with authorization and abort',async()=>{const s=await harness();const controller=new AbortController();try{const r=await fetch(s.base+'/api/transmission/events',{headers,signal:controller.signal});assert.equal(r.status,200);assert.ok(r.headers.get('content-type').includes('text/event-stream'));const read=await r.body.getReader().read();assert.match(new TextDecoder().decode(read.value),/event: status/);controller.abort()}finally{controller.abort();await s.close()}});
