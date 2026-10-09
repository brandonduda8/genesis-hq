/* Genesis Foundry v0.1 — real deterministic artifact builder, not an AI worker. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const controls = ['productName', 'tagline', 'audience', 'features', 'cta', 'ctaUrl'];
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const slug = value => String(value).toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,45) || 'product';
  const palettes = {
    ember:{base:'#130f19', panel:'#231b29', color:'#f6dfc3', accent:'#e6ab72', ghost:'#9b757b', glow:'#ca6b65'},
    nebula:{base:'#100f26', panel:'#201a41', color:'#eee8ff', accent:'#ad9dff', ghost:'#686bc6', glow:'#b46cff'},
    mint:{base:'#0a2020', panel:'#123737', color:'#e3fff2', accent:'#8cdec2', ghost:'#4aa59b', glow:'#74bfcb'},
  };
  const samples = {
    music:{productName:'Aurum Audio',tagline:'Feel every detail. Rediscover your music with a listening experience designed around you.',audience:'People who live for music',features:'Personal sound presets\nFocus mode listening\nYour library, beautifully organized',cta:'Explore Aurum',ctaUrl:'#discover',theme:'ember'},
    saas:{productName:'Northstar Workspace',tagline:'One clear place for the work that matters. Give your team clarity, focus, and momentum.',audience:'Independent makers and ambitious teams',features:'Projects without the chaos\nCalm, useful collaboration\nVisible progress for every milestone',cta:'See the experience',ctaUrl:'#discover',theme:'nebula'},
  };
  let theme = 'ember';
  let current = {html:'', plan:null,sha:'',revision:0};
  function input() {
    const raw = Object.fromEntries(controls.map(key=>[key,$(key).value.trim()]));
    return {
      productName: raw.productName || 'Untitled Product',
      tagline: raw.tagline || 'Something useful, made thoughtfully.',
      audience: raw.audience || 'People who value great products',
      features: raw.features.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).slice(0,3),
      cta: raw.cta || 'Explore the product',
      ctaUrl: raw.ctaUrl,
      theme
    };
  }
  function safeHref(raw) {
    const url = (raw || '').trim();
    if (/^#[A-Za-z][A-Za-z0-9_-]{0,60}$/.test(url)) return url;
    try {const parsed = new URL(url); if(['https:','http:','mailto:'].includes(parsed.protocol)) return url;}
    catch { /* use local default */ }
    return '#discover';
  }
  function site(data) {
    const c = palettes[data.theme] || palettes.ember;
    const title=escape(data.productName), lead=escape(data.tagline), audience=escape(data.audience);
    const cta=escape(data.cta), href=escape(safeHref(data.ctaUrl));
    const features = (data.features.length ? data.features : ['Built with purpose','Designed around you','Made to move you forward']).map((f,i)=>`<article class="feature"><span class="count">0${i+1}</span><h3>${escape(f)}</h3><p>${['Made for clarity, so the experience feels effortless.','Every detail matters when you build around people.','Less friction. More of what brought you here.'][i]}</p></article>`).join('');
    return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><meta name="description" content="${lead}"><title>${title} — Official preview</title><style>
    :root{--bg:${c.base};--panel:${c.panel};--cream:${c.color};--accent:${c.accent};--ghost:${c.ghost};--glow:${c.glow}}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--cream);background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit;text-decoration:none}.wrap{max-width:1170px;padding:0 clamp(24px,5vw,70px);margin:auto}.navbar{height:84px;display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid #ffffff20}.wordmark{font-size:14px;letter-spacing:2px;font-weight:900}.wordmark span{color:var(--accent)}.navbar nav{display:flex;gap:25px;font-size:11px;color:#eae3ddba}.navcta{font-size:10px;border:1px solid #ffffff70;border-radius:3px;padding:11px 14px;letter-spacing:.3px}.hero{min-height:560px;padding-top:85px;padding-bottom:115px;position:relative;overflow:hidden;background:radial-gradient(ellipse at 80% 30%,var(--panel),transparent 55%)}.hero::after{content:"";position:absolute;right:-110px;top:62px;border:1px solid #ffffff21;width:390px;height:390px;border-radius:50%;box-shadow:0 0 0 55px #ffffff05,0 0 0 110px #ffffff04;pointer-events:none}.eyebrow{font-size:11px;letter-spacing:3px;color:var(--accent);text-transform:uppercase;font-weight:750}.hero h1{font-size:clamp(43px,7vw,90px);line-height:1.04;letter-spacing:-.063em;max-width:770px;margin:25px 0 20px;font-weight:750;position:relative;z-index:1}.hero h1 strong{color:var(--accent)}.hero p{font-size:15px;line-height:1.8;max-width:500px;color:#d5c8c4;position:relative;z-index:1}.actions{display:flex;align-items:center;gap:20px;margin-top:35px;flex-wrap:wrap;position:relative;z-index:1}.button{display:inline-block;padding:16px 24px;background:var(--accent);color:var(--bg);font-weight:800;font-size:12px;border-radius:4px}.actions small{color:#d5c8c4;font-size:11px}.ornament{position:absolute;right:7%;top:128px;width:230px;height:230px;border:2px solid var(--accent);border-radius:50%;opacity:.7;filter:drop-shadow(0 0 45px var(--glow));box-shadow:inset 0 0 70px #ffffff08;pointer-events:none}.ornament::after{content:"";position:absolute;inset:50px;border:1px solid var(--accent);border-radius:50%}.discovery{padding-top:80px;padding-bottom:100px}.discovery h2{font-size:clamp(29px,4vw,52px);letter-spacing:-2px;margin:15px 0 40px;max-width:650px}.features{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.feature{padding:28px 24px;min-height:225px;border:1px solid #ffffff23;background:linear-gradient(145deg,#ffffff0e,transparent)}.count{font-size:12px;color:var(--accent);letter-spacing:2px}.feature h3{font-size:20px;line-height:1.3;letter-spacing:-.5px;margin-top:27px}.feature p{font-size:12px;line-height:1.75;color:#b5b2bf}.closing{background:var(--panel);padding:60px 0;text-align:center}.closing h2{font-size:33px;letter-spacing:-1px;margin:12px auto}.closing p{color:#c7bfd0;font-size:13px}.bottom{padding-top:23px;padding-bottom:30px;display:flex;justify-content:space-between;font-size:11px;color:#d5cad180;gap:15px}@media(max-width:680px){.navbar nav,.ornament{display:none}.hero{min-height:470px;padding-top:70px}.hero h1{font-size:clamp(42px,9vw,62px)}.features{grid-template-columns:1fr}.feature{min-height:170px}.bottom{flex-wrap:wrap}}
    </style></head><body><header class="navbar wrap"><div class="wordmark"><span>◈</span> ${title}</div><nav><a href="#discover">Why us</a><a href="#features">Features</a></nav><a class="navcta" href="${href}"${href.startsWith('http')?' target="_blank" rel="noopener noreferrer"':''}>${cta} ↗</a></header><main><section class="hero"><div class="ornament" aria-hidden="true"></div><div class="wrap"><div class="eyebrow">An experience made for you</div><h1>Meet <strong>${title}.</strong><br>Something different.</h1><p>${lead}</p><div class="actions"><a class="button" href="${href}"${href.startsWith('http')?' target="_blank" rel="noopener noreferrer"':''}>${cta} &nbsp; ↗</a><small>Designed for ${audience}</small></div></div></section><section class="discovery wrap" id="discover"><p class="eyebrow">The details that matter</p><h2>Everything you need. Nothing you don't.</h2><div class="features" id="features">${features}</div></section><section class="closing"><div class="wrap"><p class="eyebrow">Your next favorite thing</p><h2>Built around better experiences.</h2><p>${lead}</p><a class="button" href="${href}"${href.startsWith('http')?' target="_blank" rel="noopener noreferrer"':''}>${cta} ↗</a></div></section></main><footer class="bottom wrap"><span>${title} — crafted with purpose.</span><span>Website built with Genesis Foundry · No AI execution claimed</span></footer></body></html>`;
  }
  function missionPlan(d) {
    const roles = [
      ['01','SCOUT','Customer signal','Research the target audience and comparable products; distinguish verified observations from assumptions.','Audience insight dossier'],
      ['02','ARCHITECT','Product blueprint','Write a scoped experience plan, component map and success criteria for '+d.productName+'.','Reviewed build specification'],
      ['03','BUILDER','First artifact','Produce the initial deliverable and capture its source; do not claim AI workers ran.','Working website artifact'],
      ['04','BREAKER','Stress & safety','Try malformed content, mobile layouts, broken links and interruptions. Record failing cases.','Failure and regression report'],
      ['05','AUDITOR','Independent proof','Reproduce tests, inspect artifact integrity, compare deliverable against the promised scope.','Independent verification receipt'],
      ['06','PRODUCT','Launch readiness','Prepare a plain-language demo, scope, and handoff with owner approval for any public publication.','Customer-ready launch pack'],
    ];
    return {schema_version:'genesis-foundry-mission-0.1',status:'PLANNED_NOT_EXECUTED',id:'foundry-'+slug(d.productName),created_at:new Date().toISOString(),objective:`Create and validate a first customer-facing website for ${d.productName}`,requirements:d,roles:roles.map(([order,agent,title,scope,deliverable])=>({order,agent,title,scope,deliverable,status:'PROPOSED_ONLY'})),budget:{incremental_usd:0},approval_required_for:['public_publishing','spend','outreach','credentials','production_changes'],artifact:{type:'responsive_html',generator:'DETERMINISTIC_BROWSER_LOCAL',worker_execution:'NOT_PERFORMED'}};
  }
  const roleDescriptions = {SCOUT:'Discover who will care.',ARCHITECT:'Define what great looks like.',BUILDER:'Make the first artifact.',BREAKER:'Find what could fail.',AUDITOR:'Verify the evidence.',PRODUCT:'Prepare for launch.'};
  function renderMission(p) {
    $('missionTarget').textContent=p.requirements.productName;
    $('missionCards').replaceChildren();
    for (const r of p.roles) {
      const node=document.createElement('article');node.className='mission-card';
      const role=document.createElement('div');role.className='role';role.textContent=r.order+' / '+r.agent;
      const h=document.createElement('h3');h.textContent=r.title;
      const paragraph=document.createElement('p');paragraph.textContent=roleDescriptions[r.agent]+' '+r.scope;
      const foot=document.createElement('footer');const left=document.createElement('span');left.textContent=r.deliverable;const right=document.createElement('b');right.textContent='NOT DISPATCHED';foot.append(left,right);
      node.append(role,h,paragraph,foot);$('missionCards').append(node);
    }
  }
  function proofRows() {
    $('checks').replaceChildren();
    const rows=[['Working responsive HTML generated','REAL LOCAL OUTPUT'],['Preview opens in an isolated browser frame','OBSERVABLE'],['Product inputs escaped and checked','BASIC VALIDATION'],['Exported site needs no backend','PORTABLE'],['AI builder jobs executed','NOT YET'],['Independent browser + security review','PENDING']];
    rows.forEach(([title,status])=>{const row=document.createElement('div');const mark=document.createElement('span');mark.textContent=status==='NOT YET'||status==='PENDING'?'○':'✓';const label=document.createElement('span');label.textContent=title;const value=document.createElement('small');value.textContent=status;row.append(mark,label,value);$('checks').append(row);});
  }
  function showPanel(name) {
    document.querySelectorAll('.panel').forEach(n=>n.classList.toggle('active',n.id==='panel-'+name));
    document.querySelectorAll('.nav-btn').forEach(n=>n.classList.toggle('active',n.dataset.panel===name));
    window.scrollTo({top:0,behavior:'instant'});
  }
  function save(content, name, mime) {
    const url=URL.createObjectURL(new Blob([content],{type:mime}));
    const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),12000);
  }
  async function build() {
    const data=input(), html=site(data), plan=missionPlan(data);
    current={html,plan,sha:'',revision:current.revision+1};
    const revision=current.revision;
    $('previewFrame').srcdoc=html;
    $('previewUrl').textContent='preview://'+slug(data.productName);
    $('previewStatus').textContent='BUILT';
    $('buildBadge').textContent='Working HTML generated';
    $('buildDetail').textContent='Browser-local · no AI calls';
    renderMission(plan);proofRows();
    if(window.crypto?.subtle) {
      try {const hash=await window.crypto.subtle.digest('SHA-256',new TextEncoder().encode(html));
        if(revision===current.revision){current.sha=Array.from(new Uint8Array(hash)).map(b=>b.toString(16).padStart(2,'0')).join('');$('buildDetail').textContent='SHA-256: '+current.sha.slice(0,16)+'… · local';}
      } catch {/* digest is optional */}
    }
  }
  function setSample(name) {const s=samples[name];for(const id of controls)$(id).value=s[id];theme=s.theme;updateTheme();build();}
  function updateTheme() {document.querySelectorAll('.theme-choice').forEach(b=>{const selected=b.dataset.theme===theme;b.classList.toggle('active',selected);b.setAttribute('aria-pressed',String(selected));});}
  document.querySelectorAll('.theme-choice').forEach(b=>b.addEventListener('click',()=>{theme=b.dataset.theme;updateTheme();build();}));
  document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',()=>showPanel(b.dataset.panel)));
  $('build').addEventListener('click',build);
  $('sampleSaaS').addEventListener('click',()=>setSample('saas'));
  $('sampleMusic').addEventListener('click',()=>setSample('music'));
  $('viewMission').addEventListener('click',()=>showPanel('missions'));
  $('downloadHtml').addEventListener('click',()=>{if(current.html)save(current.html,slug(current.plan.requirements.productName)+'-website.html','text/html;charset=utf-8');});
  $('downloadPlan').addEventListener('click',()=>{if(current.plan){const packet={...current.plan,artifact:{...current.plan.artifact,sha256:current.sha||null}};save(JSON.stringify(packet,null,2)+'\n',slug(current.plan.requirements.productName)+'-work-order.json','application/json');}});
  build();
  window.GenesisFoundry={version:'0.1',getStatus:()=>({artifact_ready:!!current.html,model_execution:'NOT_IMPLEMENTED',mission_status:current.plan?.status,artifact_sha256:current.sha,roles:current.plan?.roles.length})};
})();