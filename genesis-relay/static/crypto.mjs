// Genesis synthetic-only relay encryption + local encrypted NetBird record.
// Secrets never leave this browser via the relay API.
const enc = new TextEncoder();
const dec = new TextDecoder();
export function b64url(data) {
  const buf = data instanceof Uint8Array ? data : new Uint8Array(data);
  let s = ''; for (const b of buf) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function unb64url(s) {
  if (typeof s !== 'string' || !/^[A-Za-z0-9_-]+$/.test(s)) throw Error('Bad encoding');
  const raw = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - s.length % 4) % 4));
  return Uint8Array.from(raw, ch => ch.charCodeAt(0));
}
export async function sha(data) { return new Uint8Array(await crypto.subtle.digest('SHA-256', data)); }
export function freshRoomSecret() { return crypto.getRandomValues(new Uint8Array(32)); }
export async function roomContext(secret) {
  if (!(secret instanceof Uint8Array) || secret.length !== 32) throw Error('Invalid room key');
  const room = Array.from(await sha(new Uint8Array([...enc.encode('Genesis room v1:'), ...secret])), x => x.toString(16).padStart(2, '0')).join('');
  const base = await crypto.subtle.importKey('raw', secret, 'HKDF', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({name:'HKDF',hash:'SHA-256',salt:enc.encode('GenesisRelay-v1'),info:enc.encode('browser-messages')}, base, {name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  return {room, key};
}
export async function seal(roomContext, plaintext) {
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce,additionalData:enc.encode(roomContext.room)},roomContext.key,enc.encode(plaintext));
  return {room:roomContext.room, nonce:b64url(nonce), ciphertext:b64url(ciphertext)};
}
export async function open(roomContext, envelope) {
  if (envelope.room !== undefined && envelope.room !== roomContext.room) throw Error('Wrong room');
  const nonce=unb64url(envelope.nonce);
  if(nonce.length!==12)throw Error('Bad nonce');
  const bytes=await crypto.subtle.decrypt({name:'AES-GCM',iv:nonce,additionalData:enc.encode(roomContext.room)},roomContext.key,unb64url(envelope.ciphertext));
  return dec.decode(bytes);
}
const VAULT_KDF_ITERATIONS = 600000;
export async function encryptLocalRecord(secret, passphrase) {
  if(typeof secret!=='string'|| !secret.trim())throw Error('No key entered');
  if(typeof passphrase!=='string'|| passphrase.length<16)throw Error('Use a long master passphrase (16+ characters)');
  const salt=crypto.getRandomValues(new Uint8Array(16));
  const nonce=crypto.getRandomValues(new Uint8Array(12));
  const base=await crypto.subtle.importKey('raw',enc.encode(passphrase),'PBKDF2',false,['deriveKey']);
  const key=await crypto.subtle.deriveKey({name:'PBKDF2',hash:'SHA-256',salt,iterations:VAULT_KDF_ITERATIONS},base,{name:'AES-GCM',length:256},false,['encrypt']);
  const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce,additionalData:enc.encode('genesis-netbird-local-v1')},key,enc.encode(secret));
  return {v:1,kdf:'PBKDF2-SHA256',iterations:VAULT_KDF_ITERATIONS,salt:b64url(salt),nonce:b64url(nonce),ciphertext:b64url(ciphertext)};
}
export async function decryptLocalRecord(record,passphrase) {
  if(!record||record.v!==1||record.kdf!=='PBKDF2-SHA256'||record.iterations!==VAULT_KDF_ITERATIONS)throw Error('Unsupported vault format');
  const salt=unb64url(record.salt),nonce=unb64url(record.nonce);
  if(salt.length!==16||nonce.length!==12)throw Error('Corrupt encrypted record');
  const base=await crypto.subtle.importKey('raw',enc.encode(passphrase),'PBKDF2',false,['deriveKey']);
  const key=await crypto.subtle.deriveKey({name:'PBKDF2',hash:'SHA-256',salt,iterations:record.iterations},base,{name:'AES-GCM',length:256},false,['decrypt']);
  const raw=await crypto.subtle.decrypt({name:'AES-GCM',iv:nonce,additionalData:enc.encode('genesis-netbird-local-v1')},key,unb64url(record.ciphertext));
  return dec.decode(raw);
}
