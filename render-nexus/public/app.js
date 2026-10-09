const $=id=>document.getElementById(id);
const token=()=>$('ownerToken').value.trim();
async function api(path,init={}) {
 const headers={...(init.headers||{})};
 headers.authorization='Bearer '+token();
 const r=await fetch(path,{...init,headers});
 const data=await r.json();
 if(!r.ok) throw Error(data.error||'Request unsuccessful');
 return data;
}
function node(tag,value,cls) {
 const n=document.createElement(tag); n.textContent=value;
 if(cls)n.className=cls;return n;
}
async function health(){
 try {
  const s=await(await fetch('/api/health')).json();
  $('gateway').textContent=s.gateway_ready?'CONFIGURED':'SETUP REQUIRED';
  $('gatewayNote').textContent=s.owner_auth_configured?'Owner access configured':'Owner access missing';
  $('mailbox').textContent=s.github_transport_configured?'CONFIGURED':'NOT LINKED';
 } catch { $('gateway').textContent='OFFLINE'; }
}
async function refresh(){
 $('refresh').disabled=true;
 try{
  const data=await api('/api/feed');
  $('feed').replaceChildren();
  for(const g of data.routes){
   if(!g.items.length)continue;
   $('feed').append(node('h3',g.route.toUpperCase(),'route-title'));
   for(const item of g.items){
    const article=node('article','','feeditem');
    article.append(node('strong',item.title||'Mailbox commit'));
    article.append(node('small',item.at?new Date(item.at).toLocaleString():'Time unavailable'));
    if(item.message_id){
     const b=node('button','Inspect message');
     b.onclick=()=>inspect(g.route,item.message_id);
     article.append(b);
    }
    $('feed').append(article);
   }
  }
  if(!$('feed').childNodes.length)$('feed').append(node('p','No recent mailbox commits','muted'));
 }catch(e){$('feed').replaceChildren(node('p',e.message,'muted'))}
 finally{$('refresh').disabled=false}
}
async function inspect(route,id){
 $('record').hidden=false;
 $('recordContent').textContent='Checking message integrity...';
 try{$('recordContent').textContent=JSON.stringify(await api('/api/record?route='+encodeURIComponent(route)+'&id='+encodeURIComponent(id)),null,2)}
 catch(e){$('recordContent').textContent=e.message}
}
async function dispatch(){
 $('dispatch').disabled=true;
 $('dispatchResult').textContent='Staging...';
 try{
  const result=await api('/api/message',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({recipient:$('recipient').value,content:$('objective').value})});
  $('dispatchResult').textContent=JSON.stringify(result,null,2);
 }catch(e){$('dispatchResult').textContent=e.message}
 finally{$('dispatch').disabled=false}
}
$('refresh').onclick=refresh;
$('dispatch').onclick=dispatch;
health();
