/** Genesis Alliance HQ: authenticated, inert GitHub-mailbox control gateway. */
import http from 'node:http';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { readFile } from 'node:fs/promises';

const ROOT = dirname(fileURLToPath(import.meta.url));
const MAX_BODY = 12_000;
const MESSAGE_BYTES = 8192;
const ID = /^msg-[0-9a-f]{32}$/;
const REPO = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const ROUTES = ['astra-to-claude', 'astra-to-zane', 'claude-to-astra',
  'zane-to-astra', 'claude-to-zane', 'zane-to-claude', 'penguin-to-astra'];
const RECIPIENTS = new Set(['claude', 'zane']);
const publicFiles = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/app.css', ['app.css', 'text/css; charset=utf-8']],
]);

function digest(s) { return crypto.createHash('sha256').update(s).digest('hex'); }
function safeEqual(a, b) {
  if (!a || !b || typeof a !== 'string' || typeof b !== 'string') return false;
  return crypto.timingSafeEqual(Buffer.from(digest(a)), Buffer.from(digest(b)));
}
function canon(v) {
  if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
  if (v !== null && typeof v === 'object') {
    return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}';
  }
  return JSON.stringify(v);
}
function securityHeaders(type='application/json; charset=utf-8') {
  return {
    'content-type': type, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer', 'x-frame-options': 'DENY',
    'content-security-policy': "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; script-src 'self'; style-src 'self'; connect-src 'self'",
  };
}
function send(res, status, value) {
  res.writeHead(status, securityHeaders());
  res.end(JSON.stringify(value));
}
function fail(status, msg) { const e = new Error(msg); e.status=status; return e; }
async function bodyJSON(req) {
  if (!(req.headers['content-type'] || '').toLowerCase().startsWith('application/json')) throw fail(415, 'JSON required');
  let size=0; const chunks=[];
  for await (const chunk of req) {
    size+=chunk.length;
    if(size>MAX_BODY) throw fail(413, 'Request too large');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw fail(400, 'Invalid JSON'); }
}
function makeEnvelope(recipient, content, id, at) {
  const envelope = {schema_version:'1', message_id:id, conversation_id:'genesis-alliance-hq',
    sender:'astra', recipient, created_at:at, msg_type:'message', content,
    content_sha256:digest(content), attachments:[]};
  return {envelope, envelope_sha256:digest(canon(envelope)), staged_at:at,
    status:'staged', transport:'github-mailbox'};
}
function validated(record, route, id) {
  const e=record?.envelope;
  if (!e || !ID.test(id) || e.message_id !== id ||
      route !== e.sender + '-to-' + e.recipient || typeof e.content !== 'string' ||
      Buffer.byteLength(e.content, 'utf8') > 262144 ||
      digest(e.content) !== e.content_sha256 || digest(canon(e)) !== record.envelope_sha256)
    throw fail(422, 'Invalid or corrupted mailbox envelope');
  return e;
}
function parseCommit(r, commit, route) {
  const message=commit?.commit?.message || '';
  const match=message.match(/msg-[0-9a-f]{32}/);
  const valid=match && ID.test(match[0]);
  return {route, message_id:valid ? match[0] : null, at:commit?.commit?.committer?.date || null,
    commit_url:commit?.html_url || null, title:message.split('\n')[0].slice(0,130)};
}
export function createHandler({env=process.env, fetcher=fetch, clock=()=>new Date()}={}) {
  const owner=env.NEXUS_OWNER_TOKEN || '';
  const token=env.NEXUS_GITHUB_TOKEN || '';
  const repo=env.NEXUS_REPO || 'brandonduda8/astra-zane-bridge';
  const ready=!!owner && owner.length>=32 && !!token && REPO.test(repo);
  const counts=new Map();
  async function github(path, method='GET', payload=undefined) {
    if(!token || !REPO.test(repo)) throw fail(503, 'GitHub transport not configured');
    const r=await fetcher('https://api.github.com/repos/'+repo+'/'+path, {
      method, headers:{'user-agent':'genesis-alliance-hq',accept:'application/vnd.github+json',
        authorization:'Bearer '+token,'content-type':'application/json'},
      body: payload===undefined ? undefined : JSON.stringify(payload),
      signal:AbortSignal.timeout(12000),
    });
    if (r.status===404) throw fail(404, 'Mailbox record not found');
    if(!r.ok) throw fail(503, 'GitHub transport status '+r.status);
    return r.json();
  }
  async function stage(recipient, content) {
    const id='msg-'+crypto.randomUUID().replaceAll('-','');
    const record=makeEnvelope(recipient, content, id, clock().toISOString());
    const path='mailbox/astra-to-'+recipient+'/'+id+'.json';
    const bytes=Buffer.from(canon(record)+'\n').toString('base64');
    const payload={message:'mailbox: envelope '+id+' (astra->'+recipient+')',
      branch:'main',content:bytes};
    try { await github('contents/'+path,'PUT',payload); }
    catch (e) {
      // GitHub might have committed before the response was lost. Verify the exact path.
      try {
        const existing=await github('contents/'+path);
        const decoded=Buffer.from(existing.content || '', 'base64').toString('utf8');
        if (decoded.trim()!==canon(record)) throw Error('Conflicting GitHub record');
      } catch { throw fail(503, 'Delivery uncertain; check mailbox before retrying'); }
    }
    return {message_id:id, route:'astra-to-'+recipient, status:'STAGED_UNACKNOWLEDGED',
      execution:'NOT_VERIFIED', path};
  }
  async function feed() {
    const groups=await Promise.all(ROUTES.map(async route=> {
      try {
        const data=await github('commits?path=mailbox/'+route+'&per_page=5');
        return {route, ok:true, items:Array.isArray(data) ? data.map(c=>parseCommit(null,c,route)) : []};
      } catch(e) { return {route,ok:false,error:e.status===404 ? 'No history' : 'Read unavailable',items:[]}; }
    }));
    return {routes:groups, status:'COMMIT_METADATA_ONLY', note:'Commit metadata is not proof an agent received or executed a task.'};
  }
  async function record(route, id) {
    if(!ROUTES.includes(route)||!ID.test(id)) throw fail(400,'Invalid record identifier');
    const contents=await github('contents/mailbox/'+route+'/'+id+'.json?ref=main');
    const raw=Buffer.from(contents?.content || '','base64');
    if(raw.length>1048576) throw fail(413, 'Mailbox record too large');
    let value;
    try { value=JSON.parse(raw.toString('utf8')); }
    catch { throw fail(422,'Invalid record JSON'); }
    const e=validated(value,route,id);
    return {message_id:id, route, content:e.content, created_at:e.created_at,
      reply_to:e.reply_to || null, transport:'RECORDED_IN_GITHUB', execution:'NOT_VERIFIED'};
  }
  return async function handler(req,res) {
    const pathname=new URL(req.url,'http://localhost').pathname;
    try {
      // Simple process-local abuse cap; never a billing or durable security guarantee.
      const ip=req.socket?.remoteAddress || 'unknown'; const now=clock().getTime();
      const current=counts.get(ip) || {start:now, count:0};
      if (now-current.start >= 60000) {current.start=now;current.count=0;}
      current.count++;
      counts.set(ip,current);
      if(counts.size>500) counts.clear();
      if(current.count>60) throw fail(429,'Too many requests');
      if(req.method==='GET' && publicFiles.has(pathname)) {
        const [file,mime]=publicFiles.get(pathname);
        const data=await readFile(join(ROOT,'public',file));
        res.writeHead(200,securityHeaders(mime)); res.end(data); return;
      }
      if(req.method==='GET' && pathname==='/api/health') {
        return send(res,200,{name:'Genesis Alliance HQ',mode:'DEVELOPMENT',
          owner_auth_configured:owner.length>=32, github_transport_configured:!!token,
          gateway_ready:ready, model_execution:'NOT_IMPLEMENTED', live_agent_status:'UNVERIFIED'});
      }
      const auth=(req.headers.authorization || '').match(/^Bearer (\S+)$/)?.[1] || '';
      if(!owner || owner.length<32 || !safeEqual(auth,owner)) throw fail(401,'Unauthorized');
      if(req.method==='GET' && pathname==='/api/feed') return send(res,200,await feed());
      if(req.method==='GET' && pathname==='/api/record') {
        const query=new URL(req.url,'http://localhost').searchParams;
        return send(res,200,await record(query.get('route') || '',query.get('id') || ''));
      }
      if(req.method==='POST' && pathname==='/api/message') {
        if(!ready) throw fail(503,'Gateway not configured');
        const data=await bodyJSON(req);
        if(!data || !RECIPIENTS.has(data.recipient) || typeof data.content!=='string' ||
           !data.content.trim() || Buffer.byteLength(data.content,'utf8')>MESSAGE_BYTES)
          throw fail(400,'Invalid recipient or message (maximum 8192 bytes)');
        return send(res,201,await stage(data.recipient,data.content));
      }
      throw fail(404,'Not found');
    } catch(e) {
      const code=e.status || 503;
      return send(res,code,{error:code===503?'Operation unavailable':e.message,
        ...(code===503 ? {detail:'No agent execution is implied; inspect mailbox before retrying.'} : {})});
    }
  };
}

if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]) {
  const port=Number(process.env.PORT || 10000);
  http.createServer(createHandler()).listen(port,'0.0.0.0',()=>{
    console.log('Genesis Alliance HQ listening on port '+port+' (no model execution)');
  });
}
