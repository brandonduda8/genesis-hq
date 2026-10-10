import csv
import http.client
import io
import json
import pathlib
import sys
import tempfile
import threading
import unittest
import uuid

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from foundry_v02.core import Store, InputError, ConflictError
from foundry_v02.server import Server, require_safe_bind

EXAMPLE={'customer_name':'Taylor Webb','company':'Bright Ridge Plumbing',
         'email':'taylor@example.invalid','service':'Water heater repair',
         'notes':'Estimate after inspection', 'owner':'Team'}

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=pathlib.Path(self.tmp.name)/'database.sqlite'
        self.store=Store(self.db)
    def tearDown(self): self.tmp.cleanup()
    def create(self,data=None,key='once-12345678'):
        return self.store.create(data or EXAMPLE,key)

    def test_create_read_and_search(self):
        lead,created=self.create()
        self.assertTrue(created)
        self.assertEqual(lead['customer_name'],'Taylor Webb')
        self.assertEqual(lead['stage'],'new')
        self.assertEqual(lead['version'],1)
        self.assertEqual(len(self.store.list(query='ridge')),1)
        self.assertEqual(len(self.store.list(stage='won')),0)
        self.assertEqual(self.store.receipt()['lead_count'],1)

    def test_idempotent_create(self):
        a,_=self.create()
        b,new=self.create()
        self.assertFalse(new)
        self.assertEqual(a['id'],b['id'])
        self.assertEqual(self.store.receipt()['lead_count'],1)

    def test_idempotency_conflict(self):
        self.create()
        with self.assertRaises(ConflictError):
            self.create({**EXAMPLE,'customer_name':'Someone Else'})

    def test_input_validation(self):
        for bad in [{'customer_name':''},{'email':'not an email'},
                    {'customer_name':'A'*121},{'attacker_field':'value'},
                    {'service':' '}, {'notes':'z'*2500}]:
            with self.subTest(bad=bad),self.assertRaises(InputError):
                self.store.create(EXAMPLE|bad,uuid.uuid4().hex)

    def test_optimistic_stage_updates(self):
        lead,_=self.create()
        updated=self.store.update(lead['id'],{'stage':'quoted','notes':'Measured'},1)
        self.assertEqual(updated['version'],2)
        self.assertEqual(updated['stage'],'quoted')
        with self.assertRaises(ConflictError):
            self.store.update(lead['id'],{'stage':'won'},1)
        with self.assertRaises(InputError):
            self.store.update(lead['id'],{'stage':'unrecognized'},2)

    def test_quote_math_and_replace(self):
        lead,_=self.create()
        items=[{'description':'Service hours','quantity':3,'unit_price_cents':12575},
               {'description':'Parts','quantity':2,'unit_price_cents':330}]
        result=self.store.save_quote(lead['id'],items,1)
        self.assertEqual(result['quote_total_cents'],38385)
        self.assertEqual(len(result['quote_items']),2)
        result=self.store.save_quote(lead['id'],[items[0]],2)
        self.assertEqual(result['quote_total_cents'],37725)
        self.assertEqual(len(result['quote_items']),1)
        self.assertEqual(self.store.receipt()['recent_events'][0]['kind'],'QUOTE_UPDATED')

    def test_quote_rejects_price_bools_and_excess(self):
        lead,_=self.create()
        for item in [ {'description':'Broken','quantity':-1,'unit_price_cents':500},
                      {'description':'Broken','quantity':True,'unit_price_cents':500},
                      {'description':'Broken','quantity':1,'unit_price_cents':-5},
                      {'description':'Broken','quantity':1,'unit_price_cents':2**64},
                      {'description':' ','quantity':1,'unit_price_cents':50} ]:
            with self.subTest(item=item), self.assertRaises(InputError):
                self.store.save_quote(lead['id'],[item],1)
        self.assertEqual(self.store.get(lead['id'])['version'],1)

    def test_restart_persists_quote(self):
        lead,_=self.create()
        self.store.save_quote(lead['id'],[{'description':'Consult','quantity':1,'unit_price_cents':5000}],1)
        reopened=Store(self.db)
        self.assertEqual(reopened.get(lead['id'])['quote_total_cents'],5000)
        self.assertEqual(reopened.receipt()['lead_count'],1)

    def test_export_roundtrip_all_rows(self):
        for i in range(5): self.create({**EXAMPLE,'customer_name':f'Customer {i}'},key=f'export-key-{i:04}')
        export=self.store.export_data()
        self.assertEqual(export['schema_version'],'foundry.v0.2')
        self.assertEqual(len(export['leads']),5)
        lines=list(csv.reader(io.StringIO(self.store.export_csv())))
        self.assertEqual(len(lines),6)

    def test_csv_formula_escape(self):
        lead,_=self.create({**EXAMPLE,'company':'=HYPERLINK("bad")'})
        output=self.store.export_csv()
        self.assertIn("'=HYPERLINK",output)

    def test_atomic_restore_export_and_no_overwrite(self):
        lead,_=self.create()
        self.store.save_quote(lead['id'],[{'description':'Pipe repair','quantity':2,'unit_price_cents':2550}],1)
        backup=self.store.export_data()
        target=Store(pathlib.Path(self.tmp.name)/'restored.sqlite')
        self.assertEqual(target.restore_backup(backup),1)
        restored=target.get(lead['id'])
        self.assertEqual(restored['quote_total_cents'],5100)
        self.assertEqual(restored['version'],2)
        with self.assertRaises(ConflictError):target.restore_backup(backup)

    def test_bad_restore_is_atomic(self):
        target=Store(pathlib.Path(self.tmp.name)/'new.sqlite')
        first,_=self.create()
        data=self.store.export_data()
        data['leads'].append({**data['leads'][0],'id':'not-a-valid-id'})
        with self.assertRaises(InputError):target.restore_backup(data)
        self.assertEqual(target.receipt()['lead_count'],0)

    def test_demo_seed_is_synthetic_and_one_time(self):
        generated=self.store.seed_demo()
        self.assertEqual(len(generated),2)
        self.assertTrue(all(x['is_demo'] for x in generated))
        with self.assertRaises(ConflictError): self.store.seed_demo()

    def test_remote_binding_requires_protected_owner(self):
        with self.assertRaises(ValueError): require_safe_bind('0.0.0.0','')
        with self.assertRaises(ValueError): require_safe_bind('0.0.0.0','short')
        require_safe_bind('0.0.0.0','p'*32)
        require_safe_bind('127.0.0.1','')

class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.server=Server(('127.0.0.1',0),Store(pathlib.Path(self.tmp.name)/'app.sqlite'),'q'*40)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.thread.join(timeout=3);self.server.server_close();self.tmp.cleanup()
    def request(self,method,path,body=None,authorized=True,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        headers={}
        if authorized: headers['Authorization']='Bearer '+'q'*40
        if body is not None:
            headers['Content-Type']='application/json'
            headers['X-Foundry-Client']='v0.2'
            body=json.dumps(body)
        if origin:headers['Origin']=origin
        conn.request(method,path,body=body,headers=headers)
        result=conn.getresponse();raw=result.read();status=result.status;conn.close()
        try: data=json.loads(raw)
        except (ValueError,UnicodeError): data=raw.decode('utf-8')
        return status,data

    def test_unauthorized_and_health(self):
        self.assertEqual(self.request('GET','/api/health',authorized=False)[0],200)
        self.assertEqual(self.request('GET','/api/leads',authorized=False)[0],401)
        self.assertEqual(self.request('POST','/api/leads',EXAMPLE,authorized=False)[0],401)

    def test_http_end_to_end(self):
        # ID key is mandatory; API should not create arbitrary duplicates.
        self.assertEqual(self.request('POST','/api/leads',EXAMPLE)[0],400)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        headers={'Authorization':'Bearer '+'q'*40,'X-Foundry-Client':'v0.2',
                 'Content-Type':'application/json','Idempotency-Key':'api-test-abc123'}
        conn.request('POST','/api/leads',body=json.dumps(EXAMPLE),headers=headers)
        r=conn.getresponse();self.assertEqual(r.status,201);lead=json.loads(r.read());conn.close()
        stage,result=self.request('PATCH','/api/leads/'+lead['id'],{'expected_version':1,'stage':'contacted'})
        self.assertEqual(stage,200);self.assertEqual(result['version'],2)
        quote={'expected_version':2,'items':[{'description':'Test','quantity':2,'unit_price_cents':12500}]}
        stage,result=self.request('PUT','/api/leads/'+lead['id']+'/quote',quote)
        self.assertEqual(stage,200);self.assertEqual(result['quote_total_cents'],25000)
        stage,result=self.request('GET','/api/export.json')
        self.assertEqual(stage,200);self.assertEqual(len(result['leads']),1)

    def test_http_backup_restore_requires_empty_workspace(self):
        # A portable export produced by one workspace can be safely imported via the API.
        with tempfile.TemporaryDirectory() as src:
            origin=Store(pathlib.Path(src)/'origin.sqlite')
            old,_=origin.create(EXAMPLE,'restore-http-test-key')
            origin.save_quote(old['id'],[{'description':'Repair','quantity':1,'unit_price_cents':12345}],1)
            backup=origin.export_data()
        code,result=self.request('POST','/api/restore',backup)
        self.assertEqual(code,201)
        self.assertEqual(result['imported_records'],1)
        code,result=self.request('GET','/api/leads')
        self.assertEqual(code,200)
        self.assertEqual(result['leads'][0]['quote_total_cents'],12345)
        code,_=self.request('POST','/api/restore',backup)
        self.assertEqual(code,409)

    def test_csrf_origin_rejected(self):
        status,_=self.request('POST','/api/demo-seed',{},origin='https://evil.example')
        self.assertEqual(status,403)

if __name__=='__main__': unittest.main()
