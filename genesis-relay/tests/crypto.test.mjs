import test from 'node:test';
import assert from 'node:assert/strict';
import {freshRoomSecret,roomContext,seal,open,b64url,unb64url,encryptLocalRecord,decryptLocalRecord} from '../static/crypto.mjs';

test('room key generated with 256 bits entropy',()=>assert.equal(freshRoomSecret().length,32));
test('random room keys differ',()=>assert.notDeepEqual(freshRoomSecret(),freshRoomSecret()));
test('b64url roundtrip',()=>assert.deepEqual(unb64url(b64url(freshRoomSecret())).length,32));
test('message encrypts and decrypts',async()=>{const c=await roomContext(freshRoomSecret());const e=await seal(c,'synthetic GENESIS_ACK');assert.notEqual(e.ciphertext,'synthetic GENESIS_ACK');assert.equal(await open(c,e),'synthetic GENESIS_ACK')});
test('wrong room key rejects',async()=>{const c=await roomContext(freshRoomSecret());const other=await roomContext(freshRoomSecret());const e=await seal(c,'hello');await assert.rejects(()=>open(other,e))});
test('tampered ciphertext fails authentication',async()=>{const c=await roomContext(freshRoomSecret());const m=await seal(c,'hello');m.ciphertext=(m.ciphertext[0]==='A'?'B':'A')+m.ciphertext.slice(1);await assert.rejects(()=>open(c,m))});
test('local vault encrypts and decrypts with passphrase',async()=>{const blob=await encryptLocalRecord('test-netbird-key-not-real','this-is-a-very-long-passphrase');assert.equal(blob.v,1);assert.ok(!JSON.stringify(blob).includes('test-netbird-key-not-real'));assert.equal(await decryptLocalRecord(blob,'this-is-a-very-long-passphrase'),'test-netbird-key-not-real')});
test('vault rejects weak passphrases',async()=>{await assert.rejects(()=>encryptLocalRecord('test-only','123456'))});
test('vault rejects wrong passphrase',async()=>{const b=await encryptLocalRecord('test','correct-horse-battery-staple');await assert.rejects(()=>decryptLocalRecord(b,'incorrect-passphrase-long'))});
test('vault detects ciphertext tampering',async()=>{const b=await encryptLocalRecord('test','correct-horse-battery-staple');b.ciphertext=(b.ciphertext[0]==='A'?'B':'A')+b.ciphertext.slice(1);await assert.rejects(()=>decryptLocalRecord(b,'correct-horse-battery-staple'))});
test('vault format fails closed',async()=>{await assert.rejects(()=>decryptLocalRecord({v:2},'long-long-passphrase'))});
