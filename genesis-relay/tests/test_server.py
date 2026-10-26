import http.client
import json
import pathlib
import threading
import unittest
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from server import Handler, Store, serve

ROOM = 'a' * 64
BODY = {"room": ROOM, "nonce": "Z2VuZXNpc3Rlc3QwMTI", "ciphertext": "ZmFrZWNpcGhlcnRleHRhYmNkZWY"}

class TestHandler(Handler):
    store = Store()

class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve(0, TestHandler)
        cls.port = cls.srv.server_port
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.t.join(timeout=4)

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        h = dict(headers or {})
        if body is not None:
            h.setdefault('Content-Type', 'application/json')
            body = json.dumps(body)
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        payload = r.read()
        status, hdr = r.status, dict(r.getheaders())
        c.close()
        return status, hdr, payload

    def test_health(self):
        s,h,b = self.req('GET','/health')
        self.assertEqual(s,200)
        self.assertEqual(json.loads(b)['persistent'],False)
        self.assertEqual(h['Cache-Control'],'no-store')

    def test_page_secure_headers(self):
        s,h,b = self.req('GET','/')
        self.assertEqual(s,200)
        self.assertIn(b'NetBird setup key',b)
        self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        self.assertEqual(h['X-Frame-Options'],'DENY')

    def test_static_files(self):
        for p in ['/app.js','/crypto.mjs','/style.css']:
            s,h,b=self.req('GET',p)
            self.assertEqual(s,200)
            self.assertGreater(len(b),500)

    def test_reject_unknown(self):
        s,h,b=self.req('GET','/admin')
        self.assertEqual(s,404)

    def test_reject_unbounded_body(self):
        s,h,b=self.req('POST','/api/v1/messages',{}, {'Content-Length':str(999999)})
        self.assertEqual(s,413)

    def test_reject_wrong_content_type(self):
        s,h,b=self.req('POST','/api/v1/messages',BODY, {'Content-Type':'text/plain'})
        self.assertEqual(s,415)

    def test_reject_csrf_origin(self):
        s,h,b=self.req('POST','/api/v1/messages',BODY, {'Origin':'https://attacker.invalid'})
        self.assertEqual(s,403)

    def test_reject_untrusted_fields(self):
        s,h,b=self.req('POST','/api/v1/messages',{**BODY,'secret':'never'})
        self.assertEqual(s,400)

    def test_messages_are_opaque(self):
        s,h,b=self.req('POST','/api/v1/messages',BODY)
        self.assertEqual(s,201)
        s,h,b=self.req('GET','/api/v1/messages?room='+ROOM)
        self.assertEqual(s,200)
        msg=json.loads(b)['messages'][-1]
        self.assertEqual(msg['ciphertext'],BODY['ciphertext'])
        self.assertNotIn('plaintext',msg)
        self.assertNotIn('secret',msg)
        self.assertEqual(h['Cache-Control'],'no-store')

    def test_cursor(self):
        store=Store()
        store.append('b'*64,BODY['nonce'],BODY['ciphertext'],'test')
        store.append('b'*64,BODY['nonce'],BODY['ciphertext'],'test')
        self.assertEqual(len(store.list('b'*64,after=1)),1)

    def test_per_ip_rate_limit(self):
        store=Store()
        for _ in range(20):
            self.assertIsNotNone(store.append('b'*64,BODY['nonce'],BODY['ciphertext'],'test')[0])
        _,err=store.append('b'*64,BODY['nonce'],BODY['ciphertext'],'test')
        self.assertEqual(err,'rate_limit')

    def test_ephemeral_restart(self):
        first=Store()
        first.append('b'*64,BODY['nonce'],BODY['ciphertext'],'test')
        self.assertEqual(len(first.list('b'*64)),1)
        self.assertEqual(Store().list('b'*64),[])

    def test_bad_room(self):
        s,h,b=self.req('GET','/api/v1/messages?room=abc')
        self.assertEqual(s,400)

    def test_no_network_or_secret_api(self):
        s,h,b=self.req('GET','/api/v1/keys')
        self.assertEqual(s,404)

if __name__=='__main__':unittest.main()
