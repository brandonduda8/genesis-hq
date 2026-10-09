import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';

const defaults={productName:'Aurum Audio',tagline:'Feel every detail.',audience:'Music lovers',features:'Personal sound presets\nFocus mode\nElegant library',cta:'Explore Aurum',ctaUrl:'#discover'};
function harness() {
  const elements=new Map(); const downloads=[]; const classes=new Set();
  class Element {
    constructor(id=''){this.id=id;this.children=[];this.value=defaults[id]||'';this.dataset={};this.listeners={};this.classList={toggle:(_name,_enabled)=>{}};this.attributes={};this.textContent='';this.srcdoc='';}
    addEventListener(name,fn){this.listeners[name]=fn;}
    click(){this.listeners.click?.();}
    append(...n){this.children.push(...n);}
    remove(){}
    replaceChildren(...n){this.children=n;}
    setAttribute(key,value){this.attributes[key]=value;}
  }
  const ids=['productName','tagline','audience','features','cta','ctaUrl','previewFrame','previewUrl','previewStatus','buildBadge','buildDetail','missionTarget','missionCards','checks','build','sampleMusic','sampleSaaS','viewMission','downloadHtml','downloadPlan'];
  for(const id of ids)elements.set(id,new Element(id));
  const themes=['ember','nebula','mint'].map(t=>{const el=new Element();el.dataset.theme=t;return el;});
  const navs=['studio','missions','proof'].map(t=>{const el=new Element();el.dataset.panel=t;return el;});
  const document={getElementById:id=>elements.get(id),querySelectorAll:s=>s==='.theme-choice'?themes:s==='.nav-btn'?navs:s==='.panel'?panels:[],createElement:tag=>{const el=new Element();el.tagName=tag;if(tag==='a')el.click=()=>downloads.push({name:el.download,href:el.href});return el;},body:{append(){}}};
  const panels=['studio','missions','proof'].map(t=>{const el=new Element();el.id='panel-'+t;return el;});
  const url={createObjectURL:()=>`blob:demo-${downloads.length}`,revokeObjectURL:()=>{}};
  const ctx={document,window:{crypto:webcrypto,scrollTo(){}},URL:url,Blob,TextEncoder,setTimeout:()=>0,console};
  vm.runInNewContext(fs.readFileSync(new URL('./app.js',import.meta.url),'utf8'),ctx,{filename:'app.js'});
  return {elements,document,downloads,click:id=>elements.get(id).click(),status:()=>ctx.window.GenesisFoundry.getStatus()};
}
test('builds an actual complete HTML artifact with three feature cards',()=>{const h=harness(),html=h.elements.get('previewFrame').srcdoc;assert.match(html,/<!doctype html>/);assert.match(html,/Aurum Audio/);assert.match(html,/Personal sound presets/);assert.equal((html.match(/class="feature"/g)||[]).length,3);});
test('no AI execution or false agent readiness is reported',()=>{const h=harness(),s=h.status();assert.equal(s.artifact_ready,true);assert.equal(s.model_execution,'NOT_IMPLEMENTED');assert.equal(s.mission_status,'PLANNED_NOT_EXECUTED');assert.equal(s.roles,6);});
test('template escapes executable HTML in all user fields',()=>{const h=harness();h.elements.get('productName').value='<script>alert(1)</script>';h.elements.get('tagline').value='<img src=x onerror=alert(1)>';h.click('build');const html=h.elements.get('previewFrame').srcdoc;assert.doesNotMatch(html,/<script>alert/);assert.doesNotMatch(html,/<img src=x onerror/);assert.match(html,/&lt;script&gt;/);assert.match(html,/&lt;img/);});
test('invalid javascript URL is rejected in favor of safe local link',()=>{const h=harness();h.elements.get('ctaUrl').value='javascript:alert(1)';h.click('build');const html=h.elements.get('previewFrame').srcdoc;assert.doesNotMatch(html,/href="javascript:/);assert.match(html,/href="#discover"/);});
test('new SaaS sample produces different real output',()=>{const h=harness();h.click('sampleSaaS');assert.match(h.elements.get('previewFrame').srcdoc,/Northstar Workspace/);assert.match(h.elements.get('previewFrame').srcdoc,/Projects without the chaos/);});
test('work order lists distinct roles, proposed-only, with no self-dispatch',()=>{const h=harness();const cards=h.elements.get('missionCards').children;assert.equal(cards.length,6);assert.equal(cards.every(c=>c.children[c.children.length-1].children[1].textContent==='NOT DISPATCHED'),true);});
test('both exported files have meaningful names',()=>{const h=harness();h.click('downloadHtml');h.click('downloadPlan');assert.equal(h.downloads.length,2);assert.deepEqual(h.downloads.map(x=>x.name),['aurum-audio-website.html','aurum-audio-work-order.json']);});
test('selector changes visual identity without losing feature content',()=>{const h=harness();const before=h.elements.get('previewFrame').srcdoc;const b=h.document.querySelectorAll('.theme-choice')[1];b.click();const after=h.elements.get('previewFrame').srcdoc;assert.notEqual(before,after);assert.match(after,/#ad9dff/);assert.match(after,/Personal sound presets/);});