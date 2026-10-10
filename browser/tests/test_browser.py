import functools
import http.server
import json
import pathlib
import tempfile
import threading
import unittest
import shutil

from genesis_browser.policy import RunOptions, digest
from genesis_browser.runner import execute

HERE=pathlib.Path(__file__).resolve().parents[1]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(HERE/'fixtures')))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.origin='http://127.0.0.1:'+str(cls.server.server_port)
        cls.browser=shutil.which('chromium') or shutil.which('google-chrome')

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def plan(self):
        return {'schema':'genesis-browser-plan/v1','job_id':'local-fixture','allowed_origins':[self.origin], 'actions':[
          {'id':'go','kind':'navigate','url':self.origin+'/demo.html'},
          {'id':'title','kind':'text','role':'heading','name':'Genesis Owned Browser Fixture'},
          {'id':'fill','kind':'fill','role':'textbox','name':'Project','value':'Foundry'},
          {'id':'click','kind':'click','role':'button','name':'Create sample plan'},
          {'id':'assert','kind':'assert_text','text':'Fixture ready: Foundry'},
          {'id':'screen','kind':'screenshot'},
          {'id':'snap','kind':'snapshot'},
        ]}

    def auth(self,plan):return {'plan_sha256':digest(plan),'approved_action_ids':['fill','click'],'purpose':'LOCAL_FIXTURE_TEST_ONLY'}

    @unittest.skipUnless(shutil.which('chromium') or shutil.which('google-chrome'), 'no installed Chromium')
    def test_real_chromium_fixture_end_to_end(self):
        p=self.plan()
        with tempfile.TemporaryDirectory() as t:
            output=pathlib.Path(t)/'evidence'
            result=execute(p,output,options=RunOptions(fixture=True,execute=True),authorization=self.auth(p),browser_binary=self.browser)
            self.assertEqual(result['execution'],'EXECUTED_NOT_INDEPENDENTLY_VERIFIED',result)
            self.assertEqual(len(result['actions']),7)
            self.assertTrue(all(x['state']=='DONE' for x in result['actions']))
            self.assertEqual(result['actions'][1]['text_preview'],'Genesis Owned Browser Fixture')
            self.assertTrue((output/'screen.png').exists())
            self.assertTrue((output/'snap-snapshot.txt').exists())
            self.assertEqual(result['artifacts'][0]['type'],'screenshot')
            self.assertTrue((output/'receipt.json').exists())
            self.assertEqual(json.loads((output/'receipt.json').read_text())['plan_sha256'],digest(p))

    @unittest.skipUnless(shutil.which('chromium') or shutil.which('google-chrome'), 'no installed Chromium')
    def test_real_chromium_no_side_effect_required(self):
        p={'schema':'genesis-browser-plan/v1','job_id':'read-only', 'allowed_origins':[self.origin], 'actions':[
         {'id':'go','kind':'navigate','url':self.origin+'/demo.html'},
         {'id':'check','kind':'assert_text','text':'This is synthetic data. No account or payment.'},
        ]}
        with tempfile.TemporaryDirectory() as t:
            result=execute(p,t+'/receipt',options=RunOptions(fixture=True,execute=True),browser_binary=self.browser)
            self.assertEqual(result['execution'],'EXECUTED_NOT_INDEPENDENTLY_VERIFIED')
            self.assertEqual([x['state'] for x in result['actions']],['DONE','DONE'])

    @unittest.skipUnless(shutil.which('chromium') or shutil.which('google-chrome'), 'no installed Chromium')
    def test_real_chromium_failing_assertion_preserves_failure(self):
        p={'schema':'genesis-browser-plan/v1','job_id':'expected-fail', 'allowed_origins':[self.origin], 'actions':[
         {'id':'go','kind':'navigate','url':self.origin+'/demo.html'},
         {'id':'check','kind':'assert_text','text':'Never on this page'},
         {'id':'screen','kind':'screenshot'},
        ]}
        with tempfile.TemporaryDirectory() as t:
            result=execute(p,t+'/receipt',options=RunOptions(fixture=True,execute=True),browser_binary=self.browser)
            self.assertEqual(result['execution'],'FAILED_ACTION')
            self.assertEqual([x['state'] for x in result['actions']],['DONE','FAILED'])
            self.assertFalse((pathlib.Path(t)/'receipt'/'screen.png').exists())


if __name__=='__main__':unittest.main()
