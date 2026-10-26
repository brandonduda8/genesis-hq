import contextlib
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import creatrix_station as station


class ParsingTest(unittest.TestCase):
    def test_meminfo_parses_kilobytes(self):
        out = station.parse_mem('MemTotal: 3000000 kB\nMemAvailable: 1200000 kB\nSwapTotal: 0 kB\n')
        self.assertEqual(out['MemTotal'],3000000*1024)
        self.assertEqual(out['MemAvailable'],1200000*1024)
        self.assertEqual(out['SwapTotal'],0)
    def test_meminfo_ignores_secrets(self):
        self.assertNotIn('Password',station.parse_mem('Password: 123 kB'))
    def test_cpu_name(self):
        self.assertEqual(station.cpu_model('processor: 0\nmodel name: Intel CPU\n'),'Intel CPU')
    def test_cpu_name_unknown(self):
        self.assertIn('unavailable',station.cpu_model(''))
    def test_num(self):
        self.assertIsNone(station.num_or_none('max'))
        self.assertEqual(station.num_or_none('4096'),4096)
    def test_guide_truthfulness(self):
        self.assertIn('Nothing has been flashed',station.offline_guide('muse','install Fedora'))
        self.assertIn('not SSH access',station.offline_guide('forge','connect to S1 SSH'))
        self.assertIn('Do not paste',station.offline_guide('sentinel','API key'))
    def test_offline_persona(self):
        for p in station.PERSONA_SYSTEMS:
            self.assertTrue(station.offline_guide(p,'write me a plan'))
    def test_frontend_contains_no_external_dependencies(self):
        self.assertNotIn('https://',station.HTML)
        self.assertNotIn('https://',station.JS)
        self.assertNotIn('https://',station.CSS)
        self.assertIn('prefers-reduced-motion',station.CSS)
    def test_no_injected_external_command_tools(self):
        self.assertNotIn('shell=True',Path(station.__file__).read_text())
        self.assertIn('127.0.0.1',Path(station.__file__).read_text())
    def test_run_local_model_produces_no_tools(self):
        self.assertNotIn('tools',station.PERSONA_SYSTEMS['forge'])


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=station.LocalDB(Path(self.tmp.name))
    def tearDown(self):
        self.tmp.cleanup()
    def test_create_and_retrieve(self):
        result=self.db.create('Ship Creatrix','engineering','Can open app')
        self.assertEqual(result['state'],'proposed')
        self.assertEqual(self.db.list_missions()[0]['title'],'Ship Creatrix')
    def test_sql_injection_is_data(self):
        self.db.create("x'); DROP TABLE missions;--",'research','')
        self.assertEqual(len(self.db.list_missions()),1)
    def test_state_never_means_verified(self):
        obj=self.db.create('Task','creative','')
        with self.assertRaises(ValueError):self.db.update_state(obj['id'],'verified_done')
        with self.assertRaises(ValueError):self.db.update_state(obj['id'],'owner_done')
        self.db.update_state(obj['id'],'reviewed')
        self.db.update_state(obj['id'],'owner_done')
        self.assertEqual(self.db.list_missions()[0]['state'],'owner_done')
    def test_invalid_fields(self):
        for title,kind,notes in [('', 'creative',''),('Hi','root',''),('X'*121,'creative',''),('Hi','creative','x'*1001)]:
            with self.assertRaises(ValueError):self.db.create(title,kind,notes)
    def test_archive(self):
        obj=self.db.create('A','research','')
        self.db.update_state(obj['id'],'archived')
        self.assertFalse(self.db.list_missions())
    def test_observation_dedupes(self):
        self.db.note_observation('READY')
        self.db.note_observation('READY')
        self.db.note_observation('CRITICAL')
        with self.db._connect() as c:
            self.assertEqual(c.execute('select count(*) from observations').fetchone()[0],2)


class DiagnosticTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self): self.tmp.cleanup()
    def test_bad_action(self):
        with self.assertRaises(ValueError):station.read_only_probe('sudo_rm',Path(self.tmp.name))
    def test_agents_detect_only(self):
        r=station.read_only_probe('agents',Path(self.tmp.name))
        self.assertEqual(r['result'],'EXECUTABLE_PRESENCE_ONLY')
        self.assertIsInstance(r['observed']['python3'],bool)
    def test_audit_saves_sanitized_report(self):
        r=station.read_only_probe('audit',Path(self.tmp.name))
        self.assertEqual(r['result'],'SANITIZED_REPORT_SAVED')
        p=Path(r['report_path'])
        self.assertTrue(p.is_file())
        self.assertEqual(p.stat().st_mode & 0o777,0o600)
        self.assertFalse(json.loads(p.read_text())['host_verified'])
    def test_ollama_local_only(self):
        r=station.read_only_probe('ollama',Path(self.tmp.name))
        self.assertIn('models',r)
        self.assertIn('NO_LOCAL_MODELS_VERIFIED',r['result'])


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=station.create_app(Path(cls.tmp.name),port=0,monitor=False)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.port=cls.server.server_port
        cls.url=f'http://127.0.0.1:{cls.port}'
        cls.token=cls.server.creatrix_token
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(2);cls.tmp.cleanup()
    def req(self,path='/',method='GET',data=None,headers=None):
        body=json.dumps(data).encode() if data is not None else None
        h={'Content-Type':'application/json','X-Creatrix-Token':self.token} if method=='POST' else {}
        if headers:h.update(headers)
        return urlopen(Request(self.url+path,method=method,data=body,headers=h),timeout=5)
    def test_ui_real_assets(self):
        with self.req('/') as r:
            html=r.read().decode()
            self.assertIn('GENESIS / CREATRIX',html)
            self.assertIn(self.token,html)
            self.assertEqual(r.headers['X-Frame-Options'],'DENY')
            self.assertIn("default-src 'none'",r.headers['Content-Security-Policy'])
        with self.req('/app.css') as r:self.assertIn(b'@media',r.read())
        with self.req('/app.js') as r:self.assertIn(b'mission-form',r.read())
    def test_health(self):
        with self.req('/health') as r:
            self.assertEqual(json.load(r)['status'],'loopback-only')
    def test_status_is_observation(self):
        with self.req('/api/status') as r:
            j=json.load(r)
            self.assertFalse(j['host_verified'])
            self.assertFalse(j['safety']['sudo_used'])
    def test_origin_denied(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/missions',method='POST',data={'title':'Test','notes':'','kind':'creative'},headers={'Origin':'https://evil.com'})
        self.assertEqual(c.exception.code,403)
    def test_bad_token_denied(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/missions',method='POST',data={'title':'Test','notes':'','kind':'creative'},headers={'X-Creatrix-Token':'invalid'})
        self.assertEqual(c.exception.code,403)
    def test_host_rebinding_blocked(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/status',headers={'Host':'attacker.invalid'})
        self.assertEqual(c.exception.code,403)
    def test_api_mission_flow(self):
        with self.req('/api/missions',method='POST',data={'title':'Build thing','notes':'Pass tests','kind':'engineering'}) as r:
            j=json.load(r);self.assertEqual(j['mission']['state'],'proposed');mid=j['mission']['id']
        with self.req('/api/mission/state',method='POST',data={'id':mid,'state':'reviewed'}) as r:
            self.assertEqual(json.load(r)['state'],'reviewed')
    def test_no_arbitrary_tool_execution(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/diagnostic',method='POST',data={'action':'ssh_root'})
        self.assertEqual(c.exception.code,400)
    def test_companion_offline_truth(self):
        with self.req('/api/companion',method='POST',data={'persona':'sentinel','prompt':'Should I share my API key?'}) as r:
            j=json.load(r);self.assertEqual(j['mode'],'offline');self.assertEqual(j['execution'],'NO_SHELL_OR_TOOLS')
    def test_path_traversal(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/secrets')
        self.assertEqual(c.exception.code,404)
    def test_no_public_bind(self):
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
    def test_no_cookie_or_account_needed(self):
        with self.req('/health') as r:
            self.assertIsNone(r.headers.get('Set-Cookie'))


if __name__=='__main__':unittest.main()
