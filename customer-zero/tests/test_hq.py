"""Actual local HTTP integration tests for Customer Zero gateway. No cloud/credentials."""
import http.client
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hq import HQServer, bridge_probe, host_snapshot

SECRET = "TEST_OWNER_TOKEN_NOT_REAL_ONLY_IN_TESTS_" + "x" * 38


class HQTests(unittest.TestCase):
    def setUp(self):
        self.server=HQServer(("127.0.0.1",0),SECRET)
        self.port=self.server.server_port
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.cookie=None
        self.csrf=None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def call(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=3)
        h={"Host":f"127.0.0.1:{self.port}",**(headers or {})}
        if body is not None:
            if not isinstance(body, (bytes,str)):
                body=json.dumps(body)
            h.setdefault("Content-Type","application/json")
        conn.request(method,path,body=body,headers=h)
        response=conn.getresponse()
        raw=response.read()
        status=response.status
        cookie=response.getheader("Set-Cookie")
        head=dict(response.getheaders())
        conn.close()
        return status,(json.loads(raw) if raw and "application/json" in head.get("Content-Type","") else raw),cookie,head

    def sign_in(self):
        st,body,cookie,_=self.call("POST","/api/session",{"owner_token":SECRET},
                                    {"Origin":f"http://127.0.0.1:{self.port}"})
        self.assertEqual(st,200,body)
        self.cookie=cookie.split(";",1)[0]
        self.csrf=body["csrf_token"]
        return body

    def test_get_health_public_only_reports_process(self):
        st,body,_,_=self.call("GET","/health")
        self.assertEqual(st,200)
        self.assertEqual(body["process"],"RUNNING")
        self.assertNotIn("secret",json.dumps(body).lower())

    def test_unauthed_session_status(self):
        st,s,_,_=self.call("GET","/api/session")
        self.assertEqual(st,200);self.assertEqual(s,{"authenticated":False})

    def test_unauthed_status_is_denied(self):
        st,b,_,_=self.call("GET","/api/status")
        self.assertEqual(st,401)
        self.assertEqual(b["error"],"LOGIN_REQUIRED")

    def test_rejects_bad_owner_token(self):
        st,b,c,_=self.call("POST","/api/session",{"owner_token":"wrong"})
        self.assertEqual(st,401);self.assertIsNone(c)

    def test_login_real_cookie_session(self):
        self.sign_in()
        st,b,_,_=self.call("GET","/api/session",headers={"Cookie":self.cookie})
        self.assertEqual(st,200);self.assertTrue(b["authenticated"])
        self.assertEqual(b["csrf_token"],self.csrf)

    def test_login_cookie_is_http_only_and_same_site(self):
        st,b,c,_=self.call("POST","/api/session",{"owner_token":SECRET})
        self.assertEqual(st,200)
        self.assertIn("HttpOnly",c);self.assertIn("SameSite=Strict",c)
        self.assertIn("Max-Age=1800",c)
        self.assertNotIn(SECRET,c)

    def test_authed_status_measured_and_never_fake(self):
        self.sign_in()
        st,b,_,_=self.call("GET","/api/status",headers={"Cookie":self.cookie})
        self.assertEqual(st,200)
        self.assertEqual(b["host"]["process"]["pid"],os.getpid())
        self.assertGreaterEqual(b["host"]["process"]["uptime_seconds"],0)
        self.assertGreater(b["host"]["host"]["disk_total_bytes_at_project"],0)
        self.assertEqual(b["worker_bridge"]["status"],"NOT_CONFIGURED")
        self.assertEqual(b["cody"]["status"],"NOT_VERIFIED_RUNNING")
        self.assertIsNone(b["cody"]["jobs_completed"])
        self.assertEqual(b["provider"]["status"],"NOT_CONNECTED")
        self.assertIsNone(b["mission_ledger"]["completed_jobs"])

    def test_origin_mismatch_is_denied(self):
        st,b,_,_=self.call("POST","/api/session",{"owner_token":SECRET},
                            {"Origin":"https://attacker.example"})
        self.assertEqual(st,403)

    def test_host_mismatch_is_denied(self):
        st,b,_,_=self.call("POST","/api/session",{"owner_token":SECRET},
                            {"Host":"attacker.example"})
        self.assertEqual(st,403)

    def test_rejects_extra_login_fields(self):
        st,b,_,_=self.call("POST","/api/session",{"owner_token":SECRET,"role":"admin"})
        self.assertEqual(st,400)

    def test_cannot_login_with_form(self):
        st,b,_,_=self.call("POST","/api/session","owner_token=abc",
                            {"Content-Type":"application/x-www-form-urlencoded"})
        self.assertEqual(st,400)

    def test_five_failed_logins_throttle(self):
        for n in range(5):
            self.assertEqual(self.call("POST","/api/session",{"owner_token":"bad"})[0],401)
        self.assertEqual(self.call("POST","/api/session",{"owner_token":SECRET})[0],429)

    def test_logout_rejects_missing_csrf(self):
        self.sign_in()
        st,b,_,_=self.call("POST","/api/logout",headers={"Cookie":self.cookie})
        self.assertEqual(st,403)
        self.assertEqual(self.call("GET","/api/status",headers={"Cookie":self.cookie})[0],200)

    def test_logout_revokes_cookie(self):
        self.sign_in()
        st,b,c,_=self.call("POST","/api/logout",headers={"Cookie":self.cookie,"X-Genesis-CSRF":self.csrf})
        self.assertEqual(st,200)
        self.assertTrue(b["signed_out"])
        self.assertIn("Max-Age=0",c)
        self.assertEqual(self.call("GET","/api/status",headers={"Cookie":self.cookie})[0],401)

    def test_cookie_tamper_denied(self):
        self.sign_in()
        self.assertEqual(self.call("GET","/api/status",headers={"Cookie":"genesis_session=invalid"})[0],401)

    def test_status_without_cookie_never_leaks(self):
        self.sign_in()
        st,b,_,_=self.call("GET","/api/status")
        self.assertEqual(st,401)
        self.assertNotIn("logical_cpus",json.dumps(b))

    def test_html_and_js_are_real_files(self):
        for file, expected in (("/",b"Owner sign in"),( "/app.js",b"credentials:'same-origin'"),("/style.css",b".panel")):
            status,raw,_,_=self.call("GET",file)
            self.assertEqual(status,200)
            self.assertIn(expected,raw)

    def test_unknown_route_rejected(self):
        self.assertEqual(self.call("POST","/api/send-money",{})[0],404)
        self.assertEqual(self.call("GET","/api/payments")[0],404)

    def test_server_nonloopback_refused(self):
        with self.assertRaises(ValueError):
            HQServer(("0.0.0.0",0),SECRET)

    def test_bootstrap_secret_required(self):
        with self.assertRaises(ValueError):
            HQServer(("127.0.0.1",0),"weak")

    def test_bridge_not_configured_claims_no_workers(self):
        self.assertEqual(bridge_probe(None)["status"],"NOT_CONFIGURED")
        self.assertEqual(bridge_probe("/file/not/found")["status"],"UNAVAILABLE")

    def test_bridge_probe_executes_only_supplied_probe_action(self):
        with tempfile.TemporaryDirectory() as root:
            script=pathlib.Path(root)/"probe.sh"
            script.write_text('echo "lane=codex status=READY detail=self-report"\n')
            status=bridge_probe(str(script))
            self.assertEqual(status["status"],"BRIDGE_PROBED")
            self.assertEqual(status["lanes"],[{"name":"codex","bridge_reported_state":"READY"}])
            self.assertIn("NOT_JOB_COMPLETION",status["evidence"])

    def test_bridge_probe_does_not_inherit_owner_secret(self):
        with tempfile.TemporaryDirectory() as root:
            script=pathlib.Path(root)/"probe.sh"
            script.write_text('if [ -n "$GENESIS_OWNER_TOKEN" ]; then exit 23; fi\necho "lane=codex status=DOWN"\n')
            old=os.environ.get("GENESIS_OWNER_TOKEN")
            os.environ["GENESIS_OWNER_TOKEN"] = SECRET
            try:
                result=bridge_probe(str(script))
            finally:
                if old is None: os.environ.pop("GENESIS_OWNER_TOKEN",None)
                else: os.environ["GENESIS_OWNER_TOKEN"]=old
            self.assertEqual(result["status"],"BRIDGE_PROBED")
            self.assertEqual(result["lanes"][0]["bridge_reported_state"],"DOWN")

    def test_session_expiry_is_real(self):
        self.sign_in()
        key=self.cookie.split("=",1)[1]
        with self.server.auth.lock:
            self.server.auth.sessions[key].expires=time.monotonic()-1
        self.assertEqual(self.call("GET","/api/status",headers={"Cookie":self.cookie})[0],401)

    def test_real_stat_not_hardcoded(self):
        s=host_snapshot(time.monotonic()-1,os.path.dirname(__file__))
        self.assertEqual(s["process"]["pid"],os.getpid())
        self.assertGreaterEqual(s["process"]["uptime_seconds"],0.9)
        self.assertGreater(s["host"]["disk_free_bytes_at_project"],0)


if __name__=="__main__": unittest.main()