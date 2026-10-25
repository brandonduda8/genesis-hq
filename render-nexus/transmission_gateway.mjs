/** Genesis Transmission: authenticated operator API + live GitHub-transport observations.
 * Existing Alliance HQ remains the authoritative owner-gated sender. This layer is
 * read-only except for deterministic PLAN/COMPARE requests with no durable effects.
 */
import http from 'node:http';
import crypto from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { assessFeed, planMessage, verifyTransportReceipt, evaluateVantages } from './transmission.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const MESSAGE_ID = /^msg-[a-f0-9]{32}$/;
const MESSAGE_MATCH = /msg-[a-f0-9]{32}/;
const ROUTES = Object.freeze(['astra-to-zane', 'zane-to-astra', 'astra-to-penguin',
  'penguin-to-astra', 'astra-to-hermes', 'hermes-to-astra']);
const HEADERS = Object.freeze({
  'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store',
  'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
  'x-frame-options': 'DENY',
  'content-security-policy': "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; script-src 'self'; style-src 'self'; connect-src 'self'",
});
function respond(res, code, body, headers={}) {
  if(res.writableEnded || res.destroyed) return;
  res.writeHead(code, {...HEADERS, ...headers}); res.end(JSON.stringify(body));
}
function err(code, message) { const x = new Error(message); x.status = code; return x; }
function authed(req, owner) {
  if (typeof owner !== 'string' || owner.length < 32) return false;
  const m = /^Bearer ([^\s]{1,256})$/.exec(req.headers.authorization || '');
  if (!m) return false;
  const a=crypto.createHash('sha256').update(m[1]).digest();
  const b=crypto.createHash('sha256').update(owner).digest();
  return crypto.timingSafeEqual(a,b);
}
async function parseJSON(req,limit=12000) {
  if(!(req.headers['content-type']||'').toLowerCase().startsWith('application/json')) throw err(415,'JSON required');
  let bytes=0;const chunks=[];
  for await (const chunk of req){bytes+=chunk.length;if(bytes>limit)throw err(413,'Request too large');chunks.push(chunk)}
  try{return JSON.parse(Buffer.concat(chunks).toString('utf8'))}catch{throw err(400,'Invalid JSON')}
}
function dataJSON(content){
  if(typeof content!=='string' || Buffer.byteLength(content,'utf8')>1_048_576) throw err(422,'Oversized remote record');
  try{return JSON.parse(content)}catch{throw err(422,'Malformed remote record')}
}
export function createTransmissionHandler({
  env=process.env, fetcher=fetch, clock=()=>new Date(),
  legacyHandler=(_req,res)=>respond(res,404,{error:'Not found'}),
}={}) {
  const owner=env.NEXUS_OWNER_TOKEN || '';
  const githubToken=env.NEXUS_GITHUB_TOKEN || '';
  const repo=env.NEXUS_REPO || 'brandonduda8/astra-zane-bridge';
  let cache={until:0, promise:null};
  let streams=0;
  const limit=new Map();
  const fixedURL='https://api.github.com/repos/'+repo+'/';
  async function github(path) {
    if (!githubToken || !REPO.test(repo)) throw err(503,'Transport not configured');
    let reply;
    try {
      reply=await fetcher(fixedURL+path, {
        headers:{accept:'application/vnd.github+json',authorization:'Bearer '+githubToken,
          'user-agent':'genesis-transmission-v1'},
        signal:AbortSignal.timeout(9000),
      });
    } catch { throw err(503,'GitHub transport unreachable from Render'); }
    if (reply.status===404) throw err(404,'Remote record missing');
    if(!reply.ok) throw err(503,'GitHub transport error');
    try {return await reply.json()} catch {throw err(503,'Invalid GitHub response')}
  }
  async function getRecord(path) {
    const obj=await github('contents/'+path+'?ref=main');
    const bytes=Buffer.from(obj.content||'', 'base64');
    if(bytes.length>1048576)throw err(413,'Mailbox file too large');
    return dataJSON(bytes.toString('utf8'));
  }
  async function getFeed() {
    const now=clock().getTime();
    if (cache.promise && now<cache.until) return cache.promise;
    const promise=(async()=>{
      const groups=await Promise.all(ROUTES.map(async route => {
        try {
          const commits=await github('commits?path='+encodeURIComponent('mailbox/'+route)+'&per_page=6');
          const items=(Array.isArray(commits)?commits:[]).map(c=>{
            const title=(c?.commit?.message||'').split('\n')[0].slice(0,140);
            const match=title.match(MESSAGE_MATCH);
            return {message_id:match?.[0]||null,at:c?.commit?.committer?.date||null,title};
          });
          return {route,ok:true,items};
        }catch{return {route,ok:false,items:[]}}
      }));
      return {routes:groups};
    })();
    cache={until:now+45_000,promise};
    return promise;
  }
  async function summary() {
    const data=githubToken ? assessFeed(await getFeed(),{now:clock().getTime()}) :
      {...assessFeed({routes:[]},{now:clock().getTime()}), transport:'GITHUB_NOT_CONFIGURED'};
    return {...data, gateway:'GENESIS_ALLIANCE_HQ_RENDER',
      zane_verified_reachable:false, github_credentials_configured:!!githubToken,
      processing:'READ_ONLY', max_auto_actions:0};
  }
  async function delivery(url) {
    const route=url.searchParams.get('route')||'';
    const id=url.searchParams.get('id')||'';
    if(!ROUTES.includes(route)||!MESSAGE_ID.test(id))throw err(400,'Invalid delivery lookup');
    const record=await getRecord('mailbox/'+route+'/'+id+'.json');
    let ack=null;
    try{ack=await getRecord('mailbox/acks/'+route.split('-to-')[1]+'/'+id+'.json')}
    catch(e){if(e.status!==404)throw e}
    return verifyTransportReceipt(record,ack,{route,id,now:clock().getTime()});
  }
  async function stream(req,res) {
    if(streams>=4)throw err(429,'Too many live streams');
    streams++;
    res.writeHead(200,{...HEADERS,'content-type':'text/event-stream; charset=utf-8',
      'connection':'keep-alive','x-accel-buffering':'no'});
    let closed=false;
    const push=async()=>{
      if(closed||res.destroyed)return;
      try{const data=await summary();if(!closed&&!res.destroyed)res.write('event: status\ndata: '+JSON.stringify(data)+'\n\n')}
      catch{if(!closed&&!res.destroyed)res.write('event: error\ndata: {"state":"TEMPORARILY_UNAVAILABLE"}\n\n')}
    };
    const timer=setInterval(()=>{void push()},45_000);
    const close=()=>{if(closed)return;closed=true;clearInterval(timer);streams--};
    res.on('close',close);
    await push();
  }
  return async function handler(req,res) {
    const url=new URL(req.url,'http://localhost');
    if(!url.pathname.startsWith('/transmission')&&!url.pathname.startsWith('/api/transmission'))
      return legacyHandler(req,res);
    try {
      const now=clock().getTime();const ip=req.socket?.remoteAddress||'unknown';
      const l=limit.get(ip)||{at:now,n:0};
      if(now-l.at>60_000){l.at=now;l.n=0}
      l.n++;limit.set(ip,l);if(limit.size>500)limit.clear();
      if(l.n>90)throw err(429,'Request rate exceeded');
      if(req.method==='GET'&&['/transmission','/transmission.js','/transmission.css'].includes(url.pathname)){
        const names={'/transmission':'transmission.html','/transmission.js':'transmission.js','/transmission.css':'transmission.css'};
        const mime=url.pathname.endsWith('.js')?'text/javascript; charset=utf-8':url.pathname.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8';
        const b=await readFile(join(HERE,'transmission-ui',names[url.pathname]));
        res.writeHead(200,{...HEADERS,'content-type':mime});res.end(b);return;
      }
      if(!authed(req,owner))throw err(401,'Owner authorization required');
      if(req.method==='GET'&&url.pathname==='/api/transmission/summary')return respond(res,200,await summary());
      if(req.method==='GET'&&url.pathname==='/api/transmission/delivery')return respond(res,200,await delivery(url));
      if(req.method==='GET'&&url.pathname==='/api/transmission/events')return await stream(req,res);
      if(req.method==='POST'&&url.pathname==='/api/transmission/plan'){
        const data=await parseJSON(req);
        return respond(res,200,planMessage(data?.content,{now:clock().getTime()}));
      }
      if(req.method==='POST'&&url.pathname==='/api/transmission/compare'){
        const data=await parseJSON(req);
        return respond(res,200,evaluateVantages(data?.reports,{now:clock().getTime()}));
      }
      return respond(res,404,{error:'Unknown transmission endpoint'});
    }catch(e){
      const code=Number.isInteger(e.status)?e.status:500;
      return respond(res,code,{error:code===503?'Transport temporarily unavailable':
        code===500?'Internal operation unavailable':e.message,
        ...(code===503?{delivery:'UNVERIFIED'}:{})});
    }
  };
}
if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]){
  const {createHandler}=await import('./server.mjs');
  const port=Number(process.env.PORT||10000);
  http.createServer(createTransmissionHandler({legacyHandler:createHandler()})).listen(port,'0.0.0.0',()=>{
    console.log('Genesis Transmission listening; owner-gated, no model execution');
  });
}
