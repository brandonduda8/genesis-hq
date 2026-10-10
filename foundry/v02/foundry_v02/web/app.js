'use strict';
const $=id=>document.getElementById(id);
let leads=[],selected=null,newMode=false,noticeTimer=0;
const usd=cents=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
const safeString=x=>String(x??'');
const statusNames={new:'New',contacted:'Contacted',quoted:'Quoted',won:'Won',lost:'Lost'};
function msg(s,error=false){const n=$('notice');n.textContent=s;n.classList.toggle('error',error);n.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>n.hidden=true,5000)}
async function api(url,options={}){
  const headers={...(options.headers||{})};
  const token=$('ownerToken').value;
  if(token)headers.Authorization='Bearer '+token;
  if(options.method){headers['Content-Type']='application/json';headers['X-Foundry-Client']='v0.2';}
  const response=await fetch(url,{...options,headers});
  if(!response.ok){let detail='';try{detail=(await response.json()).error}catch{}throw Error(detail||`Request failed (${response.status})`)}
  return response;
}
async function json(url,options){return(await api(url,options)).json()}
function el(tag,cls,content){const node=document.createElement(tag);if(cls)node.className=cls;if(content!==undefined)node.textContent=content;return node}
function stageTag(stage){const s=el('span','stage '+stage,statusNames[stage]||stage);return s}
function setMode(mode){newMode=mode==='new';$('emptyEditor').hidden=mode!=='empty';$('createEditor').hidden=mode!=='new';$('detailEditor').hidden=mode!=='detail'}
async function reload(targetId=selected?.id){try{const res=await json('/api/leads');leads=res.leads;$('seed').hidden=leads.length!==0;$('restoreBackup').hidden=leads.length!==0;metrics();renderList();if(newMode)return;if(targetId){const item=leads.find(x=>x.id===targetId);if(item){choose(item.id);return}}if(leads.length)choose(leads[0].id);else{selected=null;setMode('empty')}await receipt()}catch(e){msg(e.message,true)}}
function metrics(){const val=leads.reduce((sum,x)=>sum+x.quote_total_cents,0);$('metricTotal').textContent=leads.length;$('metricQuotes').textContent=leads.filter(x=>x.quote_items.length).length;$('metricValue').textContent=usd(val);$('metricWon').textContent=leads.filter(x=>x.stage==='won').length}
function renderList(){const list=$('leadList');list.replaceChildren();const q=$('search').value.trim().toLowerCase(),stage=$('filter').value;const shown=leads.filter(x=>(!stage||x.stage===stage)&&(!q||[x.customer_name,x.company,x.service,x.email].some(s=>s.toLowerCase().includes(q))));if(!shown.length){list.append(el('p','muted',leads.length?'No opportunities match these filters.':'No leads yet. Add your first customer or load synthetic examples.'));return}for(const lead of shown){const card=el('button','lead-card'+(selected?.id===lead.id?' selected':''));card.type='button';const left=el('div');left.append(el('strong','',lead.customer_name));left.append(el('small','',lead.company||lead.service));const right=el('div','right');right.append(el('span','money',usd(lead.quote_total_cents)));right.append(stageTag(lead.stage));card.append(left,right);card.onclick=()=>choose(lead.id);list.append(card)}}
function choose(id){const next=leads.find(x=>x.id===id);if(!next)return;selected=next;setMode('detail');$('detailName').textContent=next.customer_name;$('demoFlag').hidden=!next.is_demo;$('recordVersion').textContent='Revision '+next.version;$('editCustomer').value=next.customer_name;$('editCompany').value=next.company;$('editEmail').value=next.email;$('editService').value=next.service;$('editOwner').value=next.owner;$('editNotes').value=next.notes;$('editStage').value=next.stage;$('quoteRows').replaceChildren();for(const item of next.quote_items)addQuoteRow(item);recalculate();renderList()}
function moneyInputToCents(raw){const text=String(raw).trim();if(!/^\d{1,7}(?:\.\d{1,2})?$/.test(text))throw Error('Prices must be positive dollar amounts with up to two decimals');const parts=text.split('.');return Number(parts[0])*100+Number((parts[1]||'').padEnd(2,'0'))}
function quoteItems(){return [...$('quoteRows').querySelectorAll('.quote-item')].map(row=>({description:row.querySelector('[data-description]').value.trim(),quantity:Number(row.querySelector('[data-qty]').value),unit_price_cents:moneyInputToCents(row.querySelector('[data-price]').value)}))}
function recalculate(){try{const items=quoteItems();$('quoteTotal').textContent=usd(items.reduce((sum,item)=>sum+item.quantity*item.unit_price_cents,0))}catch{$('quoteTotal').textContent='Check amounts'}}
function addQuoteRow(record={description:'',quantity:1,unit_price_cents:0}){if($('quoteRows').childElementCount>=20){msg('Maximum 20 quote items',true);return}const row=el('div','quote-item');const fields=[['Description','text','description',record.description],['Qty','number','qty',record.quantity],['USD','text','price',(record.unit_price_cents/100).toFixed(2)]];for(const [label,type,attr,val] of fields){const l=el('label','',label),input=el('input');input.type=type;input.value=String(val);input.setAttribute('data-'+attr,'');if(attr==='description'){input.maxLength=160;input.required=true}else if(attr==='qty'){input.min='1';input.max='1000';input.step='1'}else input.inputMode='decimal';input.addEventListener('input',recalculate);l.append(input);row.append(l)}const rem=el('button','','×');rem.type='button';rem.setAttribute('aria-label','Remove quote line');rem.onclick=()=>{row.remove();recalculate()};row.append(rem);$('quoteRows').append(row);recalculate()}
async function receipt(){try{const data=await json('/api/receipt'),events=$('events');events.replaceChildren();if(!data.recent_events.length){events.textContent='No recorded actions yet.';return}for(const event of data.recent_events.slice(0,6)){const item=el('div','event');item.append(el('span','',event.kind.replaceAll('_',' ')));item.append(el('small','',new Date(event.created_at).toLocaleString()));events.append(item)}}catch{}}
function startNew(){$('createForm').reset();selected=null;setMode('new');renderList();$('newCustomer').focus()}
$('newLead').onclick=startNew;$('cancelNew').onclick=()=>{newMode=false;if(leads.length)choose(leads[0].id);else setMode('empty')};
$('search').oninput=renderList;$('filter').onchange=renderList;
$('createForm').onsubmit=async e=>{e.preventDefault();const submit=e.submitter;submit.disabled=true;const payload={customer_name:$('newCustomer').value,company:$('newCompany').value,email:$('newEmail').value,service:$('newService').value,owner:$('newOwner').value,notes:$('newNotes').value};try{const created=await json('/api/leads',{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID().replaceAll('-','')},body:JSON.stringify(payload)});newMode=false;await reload(created.id);msg('New lead saved to the local database')}catch(ex){msg(ex.message,true)}finally{submit.disabled=false}};
$('detailForm').onsubmit=async e=>{e.preventDefault();if(!selected)return;const btn=e.submitter;btn.disabled=true;const data={expected_version:selected.version,customer_name:$('editCustomer').value,company:$('editCompany').value,email:$('editEmail').value,service:$('editService').value,owner:$('editOwner').value,stage:$('editStage').value,notes:$('editNotes').value};try{const result=await json('/api/leads/'+selected.id,{method:'PATCH',body:JSON.stringify(data)});await reload(result.id);msg('Customer changes saved')}catch(ex){msg(ex.message,true)}finally{btn.disabled=false}};
$('addItem').onclick=()=>addQuoteRow();
$('saveQuote').onclick=async()=>{if(!selected)return;const btn=$('saveQuote');btn.disabled=true;try{const items=quoteItems();const result=await json('/api/leads/'+selected.id+'/quote',{method:'PUT',body:JSON.stringify({items,expected_version:selected.version})});await reload(result.id);msg('Quote saved — '+usd(result.quote_total_cents)+' (draft only)')}catch(ex){msg(ex.message,true)}finally{btn.disabled=false}};
$('seed').onclick=async()=>{try{await json('/api/demo-seed',{method:'POST',body:'{}'});await reload();msg('Loaded two synthetic demo leads')}catch(ex){msg(ex.message,true)}};
$('refresh').onclick=()=>reload();$('ownerToken').onchange=()=>reload();
async function download(type){try{const res=await api('/api/export.'+type);const blob=await res.blob(),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=type==='json'?'foundry-backup.json':'foundry-leads.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);msg(type.toUpperCase()+' export ready')}catch(ex){msg(ex.message,true)}}
$('exportCsv').onclick=()=>download('csv');$('exportJson').onclick=()=>download('json');
$('restoreBackup').onclick=()=>$('restoreFile').click();
$('restoreFile').onchange=async()=>{
  const file=$('restoreFile').files[0];
  if(!file)return;
  if(file.size>900000){msg('Backup too large for this version',true);return}
  if(leads.length){msg('Import only works in an empty workspace',true);return}
  if(!confirm('Import this JSON backup into your empty workspace? Existing data will not be overwritten.'))return;
  try{
    const raw=await file.text();const parsed=JSON.parse(raw);
    const data=await json('/api/restore',{method:'POST',body:JSON.stringify(parsed)});
    await reload();msg('Imported '+data.imported_records+' customer records');
  }catch(ex){msg(ex.message,true)}finally{$('restoreFile').value=''}
};
reload();
