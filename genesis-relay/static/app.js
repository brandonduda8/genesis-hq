import {freshRoomSecret,b64url,unb64url,roomContext,seal,open,encryptLocalRecord,decryptLocalRecord} from './crypto.mjs';
const $=id=>document.getElementById(id);
let room=null, last=0;
const status=(id,msg)=>{$(id).textContent=msg;};
async function loadRoom(){
  try{
    const fragment=new URLSearchParams(location.hash.slice(1));
    const s=fragment.get('room');
    if(!s){room=null;return;}
    room=await roomContext(unb64url(s));last=0;
    ['copyRoom','refresh','send','message'].forEach(k=>$(k).disabled=false);
    status('roomStatus','Active test room: '+room.room.slice(0,12)+'… (temporary; no production keys)');
    await refresh();
  }catch{room=null;status('roomStatus','Invalid room invite');}
}
async function refresh(){
  if(!room)return;
  status('sendStatus','Checking ephemeral inbox…');
  try{
    const r=await fetch('/api/v1/messages?room='+room.room+'&after='+last,{cache:'no-store'});
    if(!r.ok)throw Error('HTTP '+r.status);
    const out=await r.json();
    for(const msg of out.messages){
      last=Math.max(last,msg.id);
      const row=document.createElement('div');row.className='message';
      try{row.textContent=await open(room,msg);}catch{row.textContent='[Invalid ciphertext or wrong room key]';}
      $('messages').appendChild(row);
    }
    status('sendStatus','Inbox refreshed. Messages disappear on server restart.');
  }catch(e){status('sendStatus','Could not fetch test messages: '+e.message);}
}
$('createRoom').addEventListener('click',async()=>{
  location.hash='room='+b64url(freshRoomSecret());
  $('messages').textContent='';await loadRoom();
});
$('copyRoom').addEventListener('click',async()=>{
  if(!room)return;
  try{await navigator.clipboard.writeText(location.href);status('roomStatus','Invite copied. Treat the link as a secret; share only for synthetic testing.');}
  catch{status('roomStatus','Clipboard blocked; copy URL from address bar.');}
});
$('refresh').addEventListener('click',refresh);
$('send').addEventListener('click',async()=>{
  if(!room)return;
  const msg=$('message').value.trim();if(!msg)return;
  if(msg.length>1200){status('sendStatus','Message too long');return;}
  $('send').disabled=true;
  try{
    const env=await seal(room,msg);
    const r=await fetch('/api/v1/messages',{method:'POST',headers:{'Content-Type':'application/json'},cache:'no-store',body:JSON.stringify(env)});
    if(!r.ok)throw Error('HTTP '+r.status);
    $('message').value='';await refresh();
  }catch(e){status('sendStatus','Message not delivered: '+e.message);}
  finally{$('send').disabled=false;}
});
const VAULT_KEY='genesis-netbird-local-encrypted-v1';
const keyStatus=(msg)=>status('keyStatus',msg);
let hideTimer=0;
function hideKey(){clearTimeout(hideTimer);$('keyOutput').hidden=true;$('keyOutput').textContent='';}
$('saveKey').addEventListener('click',async()=>{
  hideKey();const key=$('netbirdKey').value,pass=$('masterPass').value;
  if(!key.trim())return keyStatus('Enter a key on your own device only.');
  if(!confirm('Store an encrypted key in THIS browser only? This is a pilot and should not replace a reviewed password manager for high-value keys.'))return;
  try{
    const record=await encryptLocalRecord(key,pass);
    localStorage.setItem(VAULT_KEY,JSON.stringify(record));
    $('netbirdKey').value='';$('masterPass').value='';
    keyStatus('Encrypted record saved in local browser storage. No server upload occurred.');
  }catch(e){keyStatus('Not stored: '+e.message);}
});
$('unlockKey').addEventListener('click',async()=>{
  hideKey();
  try{
    const raw=localStorage.getItem(VAULT_KEY);
    if(!raw)throw Error('No encrypted record on this browser');
    const key=await decryptLocalRecord(JSON.parse(raw),$('masterPass').value);
    $('keyOutput').textContent=key;$('keyOutput').hidden=false;
    $('masterPass').value='';
    keyStatus('Unlocked locally. Key hidden again after 15 seconds.');
    hideTimer=setTimeout(hideKey,15000);
  }catch{keyStatus('Could not unlock: wrong passphrase or invalid record.');}
});
$('deleteKey').addEventListener('click',()=>{
  if(!confirm('Delete the ONLY browser-stored encrypted record? This cannot be undone.'))return;
  localStorage.removeItem(VAULT_KEY);hideKey();$('masterPass').value='';$('netbirdKey').value='';
  keyStatus('Local encrypted record deleted. This does not revoke the NetBird key; revoke in the official dashboard if needed.');
});
window.addEventListener('pagehide',hideKey);
window.addEventListener('hashchange',()=>{$('messages').textContent='';loadRoom()});
loadRoom();
