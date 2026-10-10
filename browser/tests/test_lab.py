import http.client
import json
import pathlib
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from genesis_browser.lab import handler_factory, make_fixture_plan

class LabTests(unittest.TestCase):
    def test_project_bounds(self):
        for name in ('','x'*51,'has\nnewline',None):
            with self.subTest(name=name),self.assertRaises(ValueError):make_fixture_plan(name)
    def test_plan_is_fixed_local_only(self):
        p=make_fixture_plan('Foundry')
        self.assertEqual(p['allowed_origins'],['http://127.0.0.1:8777'])
        self.assertEqual([a['kind'] for a in p['actions']],['navigate','text','fill','click','assert_text','screenshot'])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.srv=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(output_root=pathlib.Path(self.tmp.name)/'runs'))
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
    def req(self,verb,path,payload=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.srv.server_port,timeout=20)
        c.request(verb,path,body=(json.dumps(payload) if payload is not None else None),headers=headers or {})
        res=c.getresponse();body=res.read();status=res.status;c.close();return status,body
    def test_public_health_only(self):
        s,b=self.req('GET','/api/health');self.assertEqual(s,200)
        self.assertEqual(json.loads(b)['external_mutations'],'DENIED')
    def test_csrf_denied(self):
        s,b=self.req('POST','/api/run',{'project':'test'}, {'Content-Type':'application/json'})
        self.assertEqual(s,403)
    def test_reject_remote_url_payload(self):
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:'+str(self.srv.server_port),'X-Genesis-Lab':'fixture-confirmed'}
        s,b=self.req('POST','/api/run',{'project':'Demo','url':'https://bank.example'},headers)
        self.assertEqual(s,400)
    def test_fixture_run_browser_and_screenshot(self):
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:'+str(self.srv.server_port),'X-Genesis-Lab':'fixture-confirmed'}
        s,b=self.req('POST','/api/run',{'project':'Foundry'},headers)
        self.assertEqual(s,200, b)
        result=json.loads(b)
        self.assertEqual(result['receipt']['execution'],'EXECUTED_NOT_INDEPENDENTLY_VERIFIED')
        self.assertEqual(len(result['receipt']['actions']),6)
        s,img=self.req('GET',result['image_url'])
        self.assertEqual(s,200)
        self.assertTrue(img.startswith(b'\x89PNG'))
        s,rcpt=self.req('GET','/api/runs/'+result['run_id']+'/receipt')
        self.assertEqual(s,200)
        self.assertEqual(json.loads(rcpt)['job_id'],'fixture-demo')

if __name__=='__main__':unittest.main()
