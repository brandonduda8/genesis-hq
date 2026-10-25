const $=id=>document.getElementById(id);
let key='',controller=null,reconnect=null,poll=null;
const safe=text=>String(text??'').replaceAll(/[\u0000-\u001f\u007f]/g,'').slice(0,500);
function setState(state){$('connection').textContent=state}
async function api(route,options={}){
  if(!key)throw Error('Connect with the owner access key first');
  const headers={authorization:'Bearer '+key,...options.headers};
  const reply=await fetch(route,{...options,headers,cache:'no-store'});
  const data=await reply.json();
  if(!reply.ok)throw Error(data.error||'Request failed');
  return data;
}
function text(tag,content,className){const el=document.createElement(tag);el.textContent=safe(content);if(className)el.className=className;return el}
function render(summary){
  $('lastCheck').textContent='Observed '+(summary.generated_at?new Date(summary.generated_at).toLocaleString():'unknown');
  $('github').textContent=summary.transport?.replace('GITHUB_','').replaceAll('_',' ')||'NOT PROBED';
  $('zane').textContent=summary.zane_verified_reachable?'VERIFIED':'UNVERIFIED';
  const area=$('lanes');area.replaceChildren();
  for(const lane of summary.route_observations||[]){
    const block=document.createElement('article');block.className='lane';
    block.append(text('b',lane.lane));
    block.append(text('small',lane.state));
    block.append(text('small',lane.last_commit_at?'Last GitHub commit '+new Date(lane.last_commit_at).toLocaleString():'No dated commit evidence'));
    area.append(block);
  }
  if(!area.childNodes.length)area.append(text('p','No mailbox metadata available','dim'));
}
async function refreshCody(){
  if(!key)return;
  try{
    const observation=await api('/api/cody/status');
    const status=observation.presence||'UNKNOWN';
    $('codyPresence').textContent=safe(status.replaceAll('_',' '));
    $('codyNote').textContent=observation.latest?
      safe('Last report '+observation.latest.observed_at+' / '+observation.latest.state):
      'No authenticated worker heartbeat yet';
  }catch{
    $('codyPresence').textContent='NOT VERIFIED';
    $('codyNote').textContent='Standby status unavailable';
  }
}
async function refresh(){
  try{render(await api('/api/transmission/summary'));setState('RENDER REACHABLE / IDENTITY UNVERIFIED')}
  catch(e){setState('NOT CONNECTED');$('github').textContent='UNAVAILABLE';$('lastCheck').textContent=safe(e.message)}
  await refreshCody();
}
async function stream(){
  controller=new AbortController();
  try{
    const r=await fetch('/api/transmission/events',{headers:{authorization:'Bearer '+key},signal:controller.signal,cache:'no-store'});
    if(!r.ok)throw Error('Stream unavailable');
    setState('LIVE STREAM CONNECTED');
    const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='';
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});
      for(let cut=buffer.indexOf('\n\n');cut!==-1;cut=buffer.indexOf('\n\n')){
        const frame=buffer.slice(0,cut);buffer=buffer.slice(cut+2);
        const dataLine=frame.split('\n').find(l=>l.startsWith('data: '));
        if(!dataLine)continue;
        try{const obj=JSON.parse(dataLine.slice(6));if(obj.route_observations)render(obj)}catch{}
      }
      if(buffer.length>256_000)buffer='';
    }
  }catch(e){if(e.name!=='AbortError')setState('STREAM INTERRUPTED / RETRYING')}
  if(key){reconnect=setTimeout(stream,60_000)}
}
function stop(){key='';$('token').value='';controller?.abort();controller=null;if(poll)clearInterval(poll);if(reconnect)clearTimeout(reconnect);poll=null;reconnect=null;setState('DISCONNECTED');$('lastCheck').textContent='Access key cleared'}
$('connect').onclick=()=>{const candidate=$('token').value.trim();stop();if(!candidate){setState('KEY REQUIRED');return}key=candidate;void refresh();void stream();poll=setInterval(()=>{void refresh()},60_000)};
$('disconnect').onclick=stop;
$('refresh').onclick=()=>void refresh();
$('plan').onclick=async()=>{try{$('planResult').textContent=JSON.stringify(await api('/api/transmission/plan',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({content:$('objective').value})}),null,2)}catch(e){$('planResult').textContent=safe(e.message)}};
$('verify').onclick=async()=>{try{const route=encodeURIComponent($('lane').value),id=encodeURIComponent($('message').value.trim());$('receiptResult').textContent=JSON.stringify(await api('/api/transmission/delivery?route='+route+'&id='+id),null,2)}catch(e){$('receiptResult').textContent=safe(e.message)}};
