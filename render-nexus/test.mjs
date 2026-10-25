import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import crypto from 'node:crypto';
import {createHandler} from './server.mjs';

const owner='x'.repeat(48);
const env={NEXUS_OWNER_TOKEN:owner,NEXUS_GITHUB_TOKEN:'fake-token',NEXUS_REPO:'brandonduda8/astra-zane-bridge'};
function remote(){
 const files=new Map();
 async function fetcher(url,options){
  const path=new URL(url).pathname;
  const prefix='/repos/brandonduda8/astra-zane-bridge/contents/';
  if(path.includes('/commits'))return Response.json([]);
  if(!path.startsWith(prefix))return Response.json({}, {status:404});
  const k=path.slice(prefix.length);
  if(options.method==='PUT'){
   const data=JSON.parse(options.body);files.set(k,data.content);
   return Response.json({commit:{sha:'example'}});
  }
  return files.has(k)?Response.json({content:files.get(k)}):Response.json({}, {status:404});
 }
 return {fetcher,files};
}
async function harness(options={}){
 const service=http.createServer(createHandler({env:options.env||env,fetcher:options.fetcher||remote().fetcher}));
 await new Promise(resolve=>service.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+service.address().port;
 return {base,close:()=>new Promise(resolve=>service.close(resolve))};
}
test('dashboard is served, no executor is claimed',async()=>{
 const s=await harness();
 try{
  assert.equal((await fetch(s.base)).status,200);
  assert.equal((await fetch(s.base+'/app.js')).status,200);
  assert.equal((await fetch(s.base+'/app.css')).status,200);
  const doctor=await(await fetch(s.base+'/api/health')).json();
  assert.equal(doctor.model_execution,'NOT_IMPLEMENTED');
 }finally{await s.close()}
});
test('owner authentication is required to read and write',async()=>{
 const s=await harness();
 try{
  assert.equal((await fetch(s.base+'/api/feed')).status,401);
  assert.equal((await fetch(s.base+'/api/record?route=zane-to-astra&id=msg-'+'a'.repeat(32))).status,401);
  assert.equal((await fetch(s.base+'/api/message',{method:'POST',headers:{'content-type':'application/json'},body:'{}'})).status,401);
 }finally{await s.close()}
});
test('a valid owner message stages a hashed inert envelope',async()=>{
 const stub=remote();const s=await harness({fetcher:stub.fetcher});
 try{
  const content='Review PR 3 without deploying';
  const response=await fetch(s.base+'/api/message',{method:'POST',headers:{authorization:'Bearer '+owner,'content-type':'application/json'},body:JSON.stringify({recipient:'claude',content})});
  assert.equal(response.status,201);
  const result=await response.json();
  assert.equal(result.status,'STAGED_UNACKNOWLEDGED');
  assert.equal(result.execution,'NOT_VERIFIED');
  const saved=JSON.parse(Buffer.from(stub.files.get(result.path),'base64').toString());
  assert.equal(saved.envelope.content,content);
  assert.equal(saved.envelope.content_sha256,crypto.createHash('sha256').update(content).digest('hex'));
 }finally{await s.close()}
});
test('invalid destination and empty objective cannot be submitted',async()=>{
 const s=await harness();
 try{
  for(const item of [{recipient:'astra',content:'hi'},{recipient:'claude',content:' '},{recipient:'zane',content:'x'.repeat(8200)}]){
   const r=await fetch(s.base+'/api/message',{method:'POST',headers:{authorization:'Bearer '+owner,'content-type':'application/json'},body:JSON.stringify(item)});
   assert.equal(r.status,400);
  }
 }finally{await s.close()}
});
test('service without GitHub token fails closed',async()=>{
 const s=await harness({env:{NEXUS_OWNER_TOKEN:owner}});
 try{
  const r=await fetch(s.base+'/api/message',{method:'POST',headers:{authorization:'Bearer '+owner,'content-type':'application/json'},body:JSON.stringify({recipient:'claude',content:'hi'})});
  assert.equal(r.status,503);
 }finally{await s.close()}
});
