/** Cody Standby: authenticated, ephemeral presence observation, never an executor.
 * Render Free process memory is not authoritative or persistent. Mission state
 * belongs in the separately verified GitHub/Genesis ledger.
 */
import crypto from 'node:crypto';

const SCHEMA = 'genesis-cody-standby/1';
const BOOT = /^[0-9a-f]{32}$/;
const STATES = new Set(['STARTING', 'STANDBY', 'MODEL_MISSING',
  'MODEL_ENDPOINT_OBSERVED', 'BLOCKED_EGRESS', 'DEGRADED', 'BLOCKED_HOST']);
const CAPABILITIES = new Set(['probe', 'receipt', 'plan', 'code', 'test']);
const MAX_SKEW_MS = 5 * 60_000;
const STALE_AFTER_MS = 75 * 60_000;
const SECURITY = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store',
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'no-referrer',
  'x-frame-options': 'DENY',
};

function respond(res, code, value) {
  if (res.destroyed || res.writableEnded) return;
  res.writeHead(code, SECURITY);
  res.end(JSON.stringify(value));
}
function matches(req, secret) {
  if (typeof secret !== 'string' || secret.length < 32 || secret.length > 256) return false;
  const token = /^Bearer ([^\s]{1,256})$/.exec(req.headers.authorization || '')?.[1];
  if (!token) return false;
  const a = crypto.createHash('sha256').update(token).digest();
  const b = crypto.createHash('sha256').update(secret).digest();
  return crypto.timingSafeEqual(a, b);
}
function fault(code, reason) {
  const error = new Error(reason); error.code = code; return error;
}
async function readJSON(req) {
  if (!(req.headers['content-type'] || '').toLowerCase().startsWith('application/json'))
    throw fault(415, 'JSON required');
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 2048) throw fault(413, 'Heartbeat too large');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw fault(400, 'Invalid JSON'); }
}
export function validatePulse(data, now) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw fault(400, 'Invalid heartbeat');
  const keys = Object.keys(data);
  const expected = ['schema', 'node', 'boot_id', 'seq', 'observed_at', 'state', 'capabilities', 'github_https', 'model_endpoint'];
  if (keys.length !== expected.length || keys.some(key => !expected.includes(key)))
    throw fault(400, 'Unexpected heartbeat fields');
  if (data.schema !== SCHEMA || data.node !== 'cody-backup' || !BOOT.test(data.boot_id) ||
      !Number.isSafeInteger(data.seq) || data.seq < 1 || data.seq > 1_000_000_000)
    throw fault(400, 'Invalid node identity or sequence');
  if (typeof data.observed_at !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(data.observed_at))
    throw fault(400, 'Invalid timestamp');
  const timestamp = Date.parse(data.observed_at);
  if (!Number.isFinite(timestamp) || Math.abs(now - timestamp) > MAX_SKEW_MS)
    throw fault(400, 'Stale or future heartbeat');
  if (!STATES.has(data.state) || !Array.isArray(data.capabilities) ||
      data.capabilities.length > 5 || new Set(data.capabilities).size !== data.capabilities.length ||
      data.capabilities.some(c => !CAPABILITIES.has(c)))
    throw fault(400, 'Invalid reported capabilities or state');
  if (![true, false, null].includes(data.github_https) ||
      ![true, false, null].includes(data.model_endpoint))
    throw fault(400, 'Invalid transport observations');
  if (data.state === 'MODEL_ENDPOINT_OBSERVED' && data.model_endpoint !== true)
    throw fault(400, 'Model endpoint observation inconsistent');
  return {
    schema: SCHEMA, node: data.node, boot_id: data.boot_id, seq: data.seq,
    observed_at: data.observed_at, state: data.state,
    capabilities: data.capabilities, github_https: data.github_https,
    model_endpoint: data.model_endpoint,
  };
}
export function createCodyGateway({
  env = process.env, clock = () => Date.now(),
  legacyHandler = (_req, res) => respond(res, 404, {error: 'Not found'}),
} = {}) {
  const owner = env.NEXUS_OWNER_TOKEN || '';
  const nodeSecret = env.NEXUS_CODY_NODE_TOKEN || '';
  const enabled = nodeSecret.length >= 32 && nodeSecret.length <= 256 && nodeSecret !== owner;
  let latest = null;
  let lastDigest = '';
  let acceptedAt = 0;
  return async function handler(req, res) {
    let path;
    try { path = new URL(req.url, 'http://localhost').pathname; }
    catch { return respond(res, 400, {error: 'Bad route'}); }
    if (path !== '/api/cody/status' && path !== '/api/cody/heartbeat')
      return legacyHandler(req, res);
    try {
      if (path === '/api/cody/status' && req.method === 'GET') {
        if (!matches(req, owner)) throw fault(401, 'Owner access required');
        const age = latest ? Math.max(0, clock() - acceptedAt) : null;
        return respond(res, 200, {
          schema: SCHEMA, node: 'cody-backup',
          receiver_configured: enabled,
          presence: !enabled ? 'RECEIVER_NOT_CONFIGURED' : !latest ? 'NO_HEARTBEAT_OBSERVED' :
            age > STALE_AFTER_MS ? 'STALE_SELF_REPORT' : 'RECENT_TOKEN_AUTHENTICATED_SELF_REPORT',
          heartbeat_age_seconds: age === null ? null : Math.floor(age / 1000),
          latest: latest ? {observed_at: latest.observed_at, state: latest.state,
            capabilities: latest.capabilities, github_https: latest.github_https,
            model_endpoint: latest.model_endpoint, seq: latest.seq} : null,
          model_inference_verified: false,
          remote_execution_enabled: false,
          note: 'Token possession and HTTP heartbeat do not prove model inference, tailnet connectivity, or job execution. State disappears when Render sleeps or restarts.',
        });
      }
      if (path === '/api/cody/heartbeat' && req.method === 'POST') {
        if (!enabled) throw fault(503, 'Cody node receiver is disabled');
        if (!matches(req, nodeSecret)) throw fault(401, 'Node access required');
        const pulse = validatePulse(await readJSON(req), clock());
        const hash = crypto.createHash('sha256').update(JSON.stringify(pulse)).digest('hex');
        if (latest && pulse.boot_id === latest.boot_id) {
          if (pulse.seq < latest.seq || (pulse.seq === latest.seq && hash !== lastDigest))
            throw fault(409, 'Stale or conflicting heartbeat sequence');
          if (pulse.seq === latest.seq)
            return respond(res, 200, {accepted: true, duplicate: true, processing: 'OBSERVATION_ONLY'});
        }
        latest = pulse;
        lastDigest = hash;
        acceptedAt = clock();
        return respond(res, 202, {accepted: true, duplicate: false,
          processing: 'OBSERVATION_ONLY', execution: 'NOT_AUTHORIZED'});
      }
      return respond(res, 405, {error: 'Method not allowed'});
    } catch (error) {
      const status = Number.isInteger(error.code) ? error.code : 500;
      return respond(res, status, {error: status === 500 ? 'Unavailable' : error.message});
    }
  };
}
