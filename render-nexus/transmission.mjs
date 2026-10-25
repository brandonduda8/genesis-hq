/** Genesis Transmission intelligence: data-only, deterministic and auditable. */
import { createHash, timingSafeEqual } from 'node:crypto';

export const VERSION = 'genesis-transmission/1';
const ID = /^msg-[0-9a-f]{32}$/;
const ROUTE = /^(astra|zane|penguin|hermes|phoenix|claude)-to-(astra|zane|penguin|hermes|phoenix|claude)$/;
const HEX = /^[a-f0-9]{64}$/;
export const digest = input => createHash('sha256').update(input).digest('hex');
export function canonical(v) {
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
  if (v !== null && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
  const s = JSON.stringify(v);
  if (s === undefined) throw new TypeError('Non-JSON value');
  return s;
}
function equalHex(a, b) {
  return typeof a === 'string' && typeof b === 'string' && HEX.test(a) && HEX.test(b) &&
    timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
}
function instant(input) {
  const ms = Date.parse(input || '');
  return Number.isFinite(ms) ? ms : null;
}
export function verifyTransportReceipt(record, ack, {route, id, now = Date.now()} = {}) {
  if (!ROUTE.test(route || '') || route.split('-to-')[0] === route.split('-to-')[1] || !ID.test(id || '') || !record || typeof record !== 'object')
    return { state: 'INVALID_REQUEST', authenticated: false };
  const e = record.envelope;
  if (!e || e.message_id !== id || `${e.sender}-to-${e.recipient}` !== route ||
      typeof e.content !== 'string' || Buffer.byteLength(e.content, 'utf8') > 262144 ||
      !equalHex(e.content_sha256, digest(e.content)) ||
      !equalHex(record.envelope_sha256, digest(canonical(e))))
    return { state: 'INVALID_ENVELOPE', authenticated: false };
  if (ack === null || ack === undefined)
    return { state: 'PUBLISHED_NO_ACK', authenticated: false, message_id: id };
  const at = instant(ack?.acked_at);
  const created = instant(e.created_at);
  if (ack?.message_id !== id || ack?.receiver !== e.recipient ||
      !equalHex(ack?.envelope_sha256, record.envelope_sha256) ||
      at === null || created === null || at < created - 300_000 || at > now + 300_000)
    return { state: 'ACK_MISMATCH', authenticated: false, message_id: id };
  return {state: 'TRANSPORT_ACK_PRESENT_IDENTITY_UNVERIFIED', authenticated: false,
    message_id: id, acknowledged_at: new Date(at).toISOString()};
}

export function assessFeed(feed, { now = Date.now() } = {}) {
  const routes = (Array.isArray(feed?.routes) ? feed.routes : []).slice(0, 30).map(group => {
    const items = Array.isArray(group.items) ? group.items.filter(x => ID.test(x.message_id || '')) : [];
    const newest = items.map(x => instant(x.at)).filter(x => x !== null && x <= now + 300_000)
      .sort((a,b) => b-a)[0] ?? null;
    const ageMin = newest === null ? null : Math.max(0, Math.round((now-newest)/60000));
    const visible = group.ok === true;
    return {lane: group.route, api_reachable: visible, records_visible: items.length,
      last_commit_at: newest === null ? null : new Date(newest).toISOString(),
      last_commit_age_minutes: ageMin,
      state: !visible ? 'GITHUB_ROUTE_UNREACHABLE' : newest === null ? 'NO_RECENT_RECORD' :
        ageMin > 60 ? 'STALE_HISTORY_ONLY' : 'RECENT_COMMIT_NOT_LIVENESS'};
  });
  const ok = routes.filter(x => x.api_reachable).length;
  const denied = routes.length-ok;
  return {
    schema: VERSION, generated_at: new Date(now).toISOString(),
    transport: routes.length===0 ? 'NO_VANTAGE_DATA' : denied===0 ? 'GITHUB_REACHABLE_FROM_RENDER_ONLY' :
      ok===0 ? 'GITHUB_UNREACHABLE_FROM_RENDER' : 'GITHUB_PARTIAL_FROM_RENDER',
    route_observations: routes, confidence: 'GITHUB_COMMIT_METADATA_ONLY',
    suspended_agents: ['claude'],
    verified_live_agents: [],
    note: 'Commits do not prove an agent read, accepted, executed or authenticated a message.'
  };
}
export function planMessage(input, { now = Date.now(), zaneEgressConfirmed = false } = {}) {
  if (typeof input !== 'string' || !input.trim() || Buffer.byteLength(input, 'utf8') > 8192)
    return {accepted:false, reason:'INVALID_MESSAGE'};
  const text=input.toLowerCase();
  const tags=[];
  const groups = [
    ['SECRETS', /\b(password|credential|private key|api[ _-]?key|secret|bearer token)\b/],
    ['FINANCIAL', /\b(payments?|invoice|bank|cashapp|paypal|credit report|withdraw|transfer funds)\b/],
    ['HOST_MUTATION', /\b(sudo|iptables|firewall|tailscale logout|tailscale up|tailscale down|reboot|disable auth|deploy|merge to main|delete files|rm -rf)\b/],
    ['EXTERNAL_ACTION', /\b(send (?:email|message)|publish publicly|contact customer|place order|outreach)\b/],
  ];
  for (const [tag,re] of groups) if(re.test(text)) tags.push(tag);
  const wantsNetwork = /\b(egress|tailscale|proxy|connection|network|connectivity|gateway)\b/.test(text);
  const wantsCode = /\b(code|test|pull request|patch|bug|implement|refactor)\b/.test(text);
  const lane = wantsNetwork ? 'zane' : wantsCode ? 'astra' : 'owner-review';
  const blocked = lane==='zane' && !zaneEgressConfirmed;
  return {schema:VERSION, accepted:true, recommended_handler:lane,
    gate: tags.length ? 'OWNER_APPROVAL_REQUIRED' : blocked ? 'BLOCKED_EGRESS' : 'DRAFT_ONLY',
    tags, suggestions: [
      ...(blocked ? ['Route through existing mailbox; no receipt until Zane acknowledges.'] : []),
      ...(tags.length ? ['Review exact requested effects before any tool execution.'] : []),
      'No automatic execution or spending; require a verified work-order receipt.'
    ],
    generated_at:new Date(now).toISOString(), autonomous_dispatch:false};
}
export function evaluateVantages(observations, {maxAgeMinutes=30, now=Date.now()}={}) {
  const valid=(Array.isArray(observations)?observations:[]).filter(r => {
    const ts=instant(r?.timestamp_utc ?? r?.measured_at ?? r?.generated_at);
    return ts!==null && ts<=now+300000 && ts>=now-maxAgeMinutes*60000 &&
      typeof r?.network_group==='string' && r.network_group.length<=64;
  });
  const groups=new Set(valid.map(r=>r.network_group));
  const statuses=valid.map(r=>({network_group:r.network_group,
    https_ok:r.https_ok===true, https_failed:r.https_ok===false}));
  return {schema:VERSION,independent_network_groups:groups.size,observations:statuses,
    classification:groups.size < 2 ? 'INSUFFICIENT_INDEPENDENT_VANTAGES' :
      statuses.some(r=>r.https_ok) && statuses.some(r=>r.https_failed) ? 'NETWORK_PATH_DIFFERENCE' :
      statuses.every(r=>r.https_ok) ? 'PUBLIC_HTTPS_OBSERVED_ON_MULTIPLE_NETWORKS' :
      statuses.every(r=>r.https_failed) ? 'MULTI_NETWORK_HTTPS_FAILURE' : 'INCONCLUSIVE',
    note:'Network labels are operator-supplied; cross-network independence needs outside confirmation.'};
}
