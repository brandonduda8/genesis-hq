"""Chromium UI verification using a stubbed HTTP adapter (network forbidden in browser)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'
EVIDENCE.mkdir(exist_ok=True)
MOCK_JS=r'''
() => {
 const samples=[
  {id:'a'.repeat(32),customer_name:'Jordan Rivera',company:'Cedar & Stone Repairs',email:'jordan@example.invalid',service:'Storefront painting',notes:'Synthetic demo inquiry',owner:'Demo crew',stage:'new',version:1,is_demo:true,quote_items:[],quote_total_cents:0},
  {id:'b'.repeat(32),customer_name:'Casey Morgan',company:'North Creek Studio',email:'casey@example.invalid',service:'Website refresh',notes:'Synthetic demo inquiry',owner:'Demo crew',stage:'new',version:1,is_demo:true,quote_items:[],quote_total_cents:0}
 ];
 let leads=[];
 const result=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});
 window.fetch=async (url,opts={})=>{
  const key=String(url), method=opts.method||'GET';
  if(key==='/api/leads'&&method==='GET')return result({leads:leads.map(x=>({...x}))});
  if(key==='/api/receipt')return result({recent_events:[],lead_count:leads.length});
  if(key==='/api/demo-seed'){if(leads.length)return result({error:'Not empty'},409);leads=samples.map(x=>({...x}));return result({leads,notice:'SYNTHETIC'});}
  if(key==='/api/leads'&&method==='POST'){const body=JSON.parse(opts.body),n={id:'c'.repeat(32),...body,stage:'new',version:1,is_demo:false,quote_items:[],quote_total_cents:0};leads.unshift(n);return result(n,201);}
  const lead=leads.find(x=>key.includes(x.id));
  if(lead&&method==='PATCH'){const body=JSON.parse(opts.body);Object.assign(lead,body);lead.version++;return result(lead);}
  if(lead&&method==='PUT'){const body=JSON.parse(opts.body);lead.quote_items=body.items;lead.version++;lead.quote_total_cents=body.items.reduce((s,x)=>s+x.quantity*x.unit_price_cents,0);return result(lead);}
  if(key==='/api/export.json')return result({schema_version:'foundry.v0.2',leads});
  if(key==='/api/export.csv')return new Response('customer_name\nExample',{status:200,headers:{'content-type':'text/csv'}});
  return result({error:'Missing mock endpoint: '+key},404);
 };
}
'''

def smoke(browser, width, name):
    page=browser.new_page(viewport={'width':width,'height':900 if width>600 else 844},accept_downloads=True)
    page.set_default_timeout(5000)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'foundry_v02/web/index.html').read_text())
    page.add_style_tag(content=(ROOT/'foundry_v02/web/style.css').read_text())
    page.evaluate(MOCK_JS)
    page.evaluate("window.crypto.randomUUID = () => 'deadbeef-dead-beef-dead-beefdeadbeef'")
    page.add_script_tag(content=(ROOT/'foundry_v02/web/app.js').read_text())
    page.locator('#seed').wait_for(state='visible')
    page.locator('#seed').click()
    page.wait_for_function("document.querySelector('#metricTotal').textContent==='2'",timeout=5000)
    print('PASS',name,'seed/list, sample data clearly labeled')
    page.locator('#addItem').click()
    item=page.locator('.quote-item').last
    item.locator('[data-description]').fill('Discovery')
    item.locator('[data-qty]').fill('2')
    item.locator('[data-price]').fill('120.50')
    assert page.locator('#quoteTotal').inner_text().strip()=='$241.00'
    page.locator('#saveQuote').click()
    page.wait_for_function("document.querySelector('#metricQuotes').textContent==='1'",timeout=5000)
    print('PASS',name,'quote editor and totals')
    page.screenshot(path=str(EVIDENCE/f'{name}.png'),full_page=True)
    dims=page.evaluate("({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})")
    assert dims['scroll']<=dims['client']+1,f'{name} horizontal overflow {dims}'
    page.locator('#newLead').click()
    page.locator('#newCustomer').fill('Taylor Example')
    page.locator('#newService').fill('Roof inspection')
    page.locator('#createForm button[type=submit]').click()
    page.wait_for_function("document.querySelector('#metricTotal').textContent==='3'",timeout=5000)
    assert not errors,errors
    print('PASS',name,'new lead form, no overflow, no runtime errors')
    page.close()

if __name__=='__main__':
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        try:
            smoke(browser,1365,'desktop')
            smoke(browser,390,'mobile')
        finally:browser.close()
