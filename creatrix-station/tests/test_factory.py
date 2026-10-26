import contextlib
from io import StringIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import threading
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cody_factory import Factory, TEMPLATE_FILES, factory_snapshot, list_workspaces, available_tools
from codyctl import inspect_scaffold, run_scaffold_tests, ssh_public_hostkey, generate_opencode_config, parser
from creatrix_station import LocalDB, create_app
from factory_mcp import handle, run, TOOLS

class FactoryBehavior(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=LocalDB(self.root)
        self.factory=Factory(self.root,self.db)
    def tearDown(self):self.tmp.cleanup()
    def test_templates_all_available(self):
        self.assertTrue({'python-cli','web-static','mcp-stdio','browser-extension','genesis-fullstack'}.issubset(TEMPLATE_FILES))
    def test_scaffold_all_templates_and_manifest(self):
        for i,t in enumerate(TEMPLATE_FILES):
            slug=f'project-{i}'
            r=self.factory.create_workspace(slug,f'Cody {i}',t)
            self.assertEqual(r['stage'],'SCAFFOLDED_NOT_EXECUTED')
            self.assertTrue(r['mission_id'])
            self.assertEqual(inspect_scaffold(self.factory,slug)['state'],'TEMPLATE_MATCH')
            self.assertEqual(self.factory.inspect_workspace(slug)['status'],'STATIC_AUDIT_ONLY')
        self.assertEqual(len(self.db.list_missions()),len(TEMPLATE_FILES))
    def test_reject_path_traversal(self):
        for name in ('../bad','/tmp/evil','a','AValid','name//bad','name\\bad','project.','one two'):
            with self.assertRaises(ValueError):self.factory.create_workspace(name,'X','python-cli')
    def test_existing_workspace_never_clobbered(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        with self.assertRaises(ValueError):self.factory.create_workspace('my-project','Different','web-static')
        self.assertEqual(list_workspaces(self.root)[0]['title'],'Fine')
    def test_user_title_control_chars_denied(self):
        with self.assertRaises(ValueError): self.factory.create_workspace('my-project','bad\nheader','python-cli')
    def test_unexpected_files_blocked(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        (self.root/'factory-projects'/'my-project'/'untrusted.py').write_text('print("x")')
        with self.assertRaises(ValueError):self.factory.inspect_workspace('my-project')
    def test_symlink_blocked(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        dest=self.root/'factory-projects'/'my-project'/'main.py'
        dest.unlink();dest.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError):self.factory.inspect_workspace('my-project')
    def test_modified_scaffold_blocks_auto_tests(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        f=self.root/'factory-projects'/'my-project'/'main.py'
        f.write_text('something else')
        self.assertEqual(inspect_scaffold(self.factory,'my-project')['state'],'BLOCKED')
        self.assertEqual(run_scaffold_tests(self.factory,'my-project',True)['state'],'BLOCKED')
    def test_tests_require_explicit_approval(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        self.assertEqual(run_scaffold_tests(self.factory,'my-project',False)['state'],'DENIED')
    def test_scaffold_executes_known_fixture_only(self):
        self.factory.create_workspace('my-project','Fine','python-cli')
        r=run_scaffold_tests(self.factory,'my-project',True)
        self.assertEqual(r['state'],'TEMPLATE_TESTS_PASS',r)
        self.assertEqual(r['exit_code'],0)
    def test_browser_extension_has_no_permissions(self):
        self.factory.create_workspace('my-project','Demo','browser-extension')
        r=run_scaffold_tests(self.factory,'my-project',True)
        self.assertEqual(r['state'],'TEMPLATE_VALIDATED');self.assertEqual(r['permissions'],[])
    def test_stdio_mcp_template_smoke(self):
        self.factory.create_workspace('my-project','Demo','mcp-stdio')
        r=run_scaffold_tests(self.factory,'my-project',True)
        self.assertEqual(r['state'],'TEMPLATE_TESTS_PASS',r)
    def test_fullstack_template_smoke(self):
        self.factory.create_workspace('my-project','Demo','genesis-fullstack')
        r=run_scaffold_tests(self.factory,'my-project',True)
        self.assertEqual(r['state'],'TEMPLATE_TESTS_PASS',r)
    def test_opencode_pairing_is_config_only(self):
        self.factory.create_workspace('my-project','Cody','python-cli')
        r=generate_opencode_config(self.factory,'my-project')
        self.assertEqual(r['state'],'CONFIG_STAGED_NOT_PAIRED')
        config=json.loads(Path(r['path']).read_text())
        self.assertEqual(config['permission']['external_directory'],'deny')
        self.assertEqual(config['permission']['bash'],'ask')
        self.assertEqual(config['mcp']['genesis-creatrix']['type'],'local')
        self.assertFalse(r['opencode_running'])
        self.assertEqual(stat.S_IMODE(Path(r['path']).stat().st_mode),0o600)
        self.assertEqual(generate_opencode_config(self.factory,'my-project')['state'],'BLOCKED')
    def test_tool_doctor_not_runtime_proof(self):
        r=factory_snapshot(self.root)
        self.assertFalse(r['auto_install'])
        self.assertIn('NOT_ENABLED',r['autonomous_execution'])
        self.assertIn('opencode',r['agent_dock'])
    def test_no_ssh_private_key_read(self):
        self.assertEqual(ssh_public_hostkey('s1-lan','bogus')['state'],'DENIED')
        with patch('codyctl.shutil.which',return_value=None):
            self.assertEqual(ssh_public_hostkey('s1-lan')['state'],'BLOCKED')
    def test_cli_requires_explicit_arguments(self):
        p=parser()
        self.assertEqual(p.parse_args(['doctor']).cmd,'doctor')
        self.assertEqual(p.parse_args(['new','project-cody','--title','Test','--template','mcp-stdio']).template,'mcp-stdio')

class MCPBehavior(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self):self.tmp.cleanup()
    def call(self,method,params=None,i=1):
        return handle({'jsonrpc':'2.0','id':i,'method':method,'params':params or {}},Path(self.tmp.name))
    def test_initialize(self):
        j=self.call('initialize');self.assertIn('protocolVersion',j['result'])
    def test_tools_all_read_only(self):
        j=self.call('tools/list');names=[x['name'] for x in j['result']['tools']]
        self.assertEqual(names,['creatrix_toolchain','creatrix_projects','creatrix_integrations'])
    def test_tool_call(self):
        j=self.call('tools/call',{'name':'creatrix_projects','arguments':{}})
        self.assertFalse(j['result']['isError'])
    def test_bad_tool(self):
        j=self.call('tools/call',{'name':'exec_remote','arguments':{}})
        self.assertEqual(j['error']['code'],-32602)
    def test_nonempty_args_rejected(self):
        j=self.call('tools/call',{'name':'creatrix_projects','arguments':{'path':'/etc/passwd'}})
        self.assertEqual(j['error']['code'],-32602)
    def test_stdio_protocol_round_trip(self):
        inp=StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
        out=StringIO()
        self.assertEqual(run(inp,out,Path(self.tmp.name)),0)
        data=[json.loads(x) for x in out.getvalue().splitlines()]
        self.assertEqual(len(data),2);self.assertEqual(data[1]['id'],2)

class FactoryHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=create_app(Path(cls.tmp.name),port=0,monitor=False)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(2);cls.tmp.cleanup()
    def req(self,path,body=None,headers=None):
        method='POST' if body is not None else 'GET'
        h={'Content-Type':'application/json','X-Creatrix-Token':self.server.creatrix_token} if body is not None else {}
        if headers: h.update(headers)
        return urlopen(Request(self.url+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers=h),timeout=5)
    def test_factory_frontend(self):
        with self.req('/') as r:
            html=r.read().decode()
            self.assertIn('data-tab="factory"',html)
            self.assertIn('Cody',html)
        with self.req('/app.js') as r:self.assertIn(b'loadFactory',r.read())
    def test_factory_snapshot(self):
        with self.req('/api/factory') as r:
            j=json.load(r);self.assertFalse(j['auto_install'])
    def test_integration_read_only(self):
        with self.req('/api/factory/integrations') as r:
            j=json.load(r);self.assertEqual(j['mcp']['status'],'LOCAL_STDIO_IMPLEMENTED')
    def test_factory_create_verify_mission(self):
        with self.req('/api/factory/create',{'slug':'cody-first','title':'First Factory','template':'mcp-stdio'}) as r:
            j=json.load(r);self.assertTrue(j['workspace']['mission_id'])
        with self.req('/api/factory/workspaces') as r:
            self.assertTrue(any(x['slug']=='cody-first' for x in json.load(r)['projects']))
        with self.req('/api/factory/inspect',{'slug':'cody-first'}) as r:
            self.assertEqual(json.load(r)['status'],'STATIC_AUDIT_ONLY')
    def test_hostile_create_denied(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/factory/create',{'slug':'../evil','title':'Bad','template':'python-cli'})
        self.assertEqual(c.exception.code,400)
    def test_origin_denied(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/factory/create',{'slug':'bad-test','title':'Bad','template':'python-cli'},headers={'Origin':'https://evil.invalid'})
        self.assertEqual(c.exception.code,403)
    def test_unknown_action_not_remote_shell(self):
        with self.assertRaises(HTTPError) as c:self.req('/api/factory/shell',{'cmd':'sudo netbird up'})
        self.assertEqual(c.exception.code,404)

if __name__=='__main__':unittest.main()
