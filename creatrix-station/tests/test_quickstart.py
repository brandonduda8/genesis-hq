import json
import os
import stat
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from importlib.util import spec_from_file_location, module_from_spec

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'creatrix_quickstart.py'
spec = spec_from_file_location('creatrix_quickstart', SOURCE)
quick = module_from_spec(spec)
spec.loader.exec_module(quick)


class QuickstartGuardTests(unittest.TestCase):
    def setUp(self):
        self.uid_patch = patch.object(os, "geteuid", return_value=1000)
        self.uid_patch.start()

    def tearDown(self):
        self.uid_patch.stop()
    def test_guard_contains_no_sudo_or_ssh_calls(self):
        self.assertNotIn('sudo ', quick.GUARD_SOURCE)
        self.assertNotIn('tailscale ', quick.GUARD_SOURCE)
        self.assertNotIn('netbird ', quick.GUARD_SOURCE)
        self.assertNotIn('ssh ', quick.GUARD_SOURCE)

    def test_install_user_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '.local/bin/genesis-creatrix-run'
            self.assertEqual(quick._create_guard(p), 'GUARD_INSTALLED_USER_ONLY')
            self.assertEqual(p.read_text(), quick.GUARD_SOURCE)
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o700)

    def test_guard_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'genesis-creatrix-run'
            quick._create_guard(p)
            self.assertEqual(quick._create_guard(p), 'GUARD_ALREADY_INSTALLED')

    def test_guard_never_overwrites_user_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'genesis-creatrix-run'
            p.write_text('my own script')
            self.assertEqual(quick._create_guard(p), 'GUARD_NOT_WRITTEN_EXISTING_FILE_DIFFERS')
            self.assertEqual(p.read_text(), 'my own script')

    def test_guard_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'target'
            target.write_text('original')
            p=Path(d)/'genesis-creatrix-run'
            p.symlink_to(target)
            self.assertEqual(quick._create_guard(p), 'GUARD_NOT_WRITTEN_EXISTING_FILE_DIFFERS')
            self.assertEqual(target.read_text(),'original')

    def test_guard_avoids_shell(self):
        self.assertIn("['systemd-run','--user','--scope'", quick.GUARD_SOURCE)
        self.assertNotIn('shell=True', quick.GUARD_SOURCE)

    def test_guard_enforces_cgroup_budget(self):
        mod=types.ModuleType('guard_test')
        exec(quick.GUARD_SOURCE,mod.__dict__)
        with patch.object(mod,'_mem',return_value={'MemTotal': 2*1024**3,'MemAvailable':400*1024**2}):
            self.assertEqual(mod.main(['--preview']),3)

    def test_guard_preview_never_starts_program(self):
        mod=types.ModuleType('guard_test')
        exec(quick.GUARD_SOURCE,mod.__dict__)
        with patch.object(mod,'_mem',return_value={'MemTotal': 4*1024**3,'MemAvailable':3*1024**3}),patch.object(mod.subprocess,'call') as c:
            self.assertEqual(mod.main(['--preview','--','echo','test']),0)
            c.assert_not_called()

    def test_guard_needs_systemd_to_run(self):
        mod=types.ModuleType('guard_test')
        exec(quick.GUARD_SOURCE,mod.__dict__)
        with patch.object(mod,'_mem',return_value={'MemTotal': 4*1024**3,'MemAvailable':3*1024**3}),patch.object(mod.shutil,'which',return_value=None):
            self.assertEqual(mod.main(['--','echo','test']),4)

    def test_guard_systemd_properties(self):
        mod=types.ModuleType('guard_test')
        exec(quick.GUARD_SOURCE,mod.__dict__)
        with patch.object(mod,'_mem',return_value={'MemTotal': 4*1024**3,'MemAvailable':3*1024**3}),patch.object(mod.shutil,'which',return_value='/usr/bin/systemd-run'),patch.object(mod.subprocess,'call',return_value=0) as c:
            self.assertEqual(mod.main(['--','python3','workload.py']),0)
            cmd=c.call_args.args[0]
            self.assertIn('MemoryMax=', ' '.join(cmd))
            self.assertIn('CPUQuota=150%',cmd)
            self.assertEqual(cmd[-2:],['python3','workload.py'])

    def test_root_refusal(self):
        with patch.object(quick.os,'geteuid',return_value=0):
            self.assertEqual(quick.main(['--label','penguin']),3)


class QuickstartDashboardTests(unittest.TestCase):
    def fixture(self):
        return {
            'schema':'genesis-creatrix-audit/1','scope':'CURRENT_LINUX_RUNTIME_ONLY',
            'memory':{'MemTotal':3*1024**3,'MemAvailable':2*1024**3,'SwapTotal':0},
            'cgroup':{'memory_events':{'oom_kill':0},'memory_pressure':{'some':{'avg10':0.2}}},
            'disk_guest_root':{'used_bytes':2*1024**3,'total_bytes':10*1024**3,'free_bytes':8*1024**3},
            'admission_plan':{'state':'AVAILABLE_FOR_ONE_BOUNDED_WORKER','reserve_bytes':800*1024**2,'proposed_worker_rss_cap_bytes':700*1024**2},
            'cpu':{'model':'Some Intel CPU','logical_processors':4,'instruction_sets':['avx2']},
            'kernel':'6.6','os':{'PRETTY_NAME':'Debian 13'},
            'reported_device_label':'penguin','collected_utc':'2026-10-26T10:00:00Z',
            'hardware_board_prior_user_report':'ELEMI', 'ports_listening_selected_only':[],
            'tools_available':{'node':True,'docker':False},'services':{'ssh':'active','netbird':'inactive'},
            'top_processes_rss_only':[{'process':'node','rss_kib':200000}],
            'swap_devices':[]
        }

    def test_dashboard_metric(self):
        html=quick.build(self.fixture())
        self.assertIn('2.00 GiB',html)
        self.assertIn('Some Intel CPU',html)
        self.assertIn('genesis-creatrix-run',html)

    def test_html_is_self_contained(self):
        html=quick.build(self.fixture())
        self.assertNotIn('<script src=',html)
        self.assertNotIn('https://',html)

    def test_escapes_malicious_data(self):
        f=self.fixture();f['cpu']['model']='<script>alert(1)</script>'
        output=quick.build(f)
        self.assertNotIn('<script>alert(1)</script>', output)
        self.assertIn('&lt;script&gt;',output)

    def test_audit_only_keeps_guard_absent(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            with patch.object(quick.Path,'home',return_value=home),patch.object(quick.os,'geteuid',return_value=1000),patch.object(quick,'collect',return_value=self.fixture()):
                result=quick.main(['--audit-only','--label','penguin'])
            self.assertEqual(result,0)
            self.assertFalse((home/'.local/bin/genesis-creatrix-run').exists())
            self.assertEqual(len(list((home/'Genesis-Creatrix/reports').glob('*/CREATRIX_AUDIT.json'))),1)

    def test_default_creates_reports_and_guard(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            with patch.object(quick.Path,'home',return_value=home),patch.object(quick.os,'geteuid',return_value=1000),patch.object(quick,'collect',return_value=self.fixture()):
                result=quick.main([])
            self.assertEqual(result,0)
            reports=list((home/'Genesis-Creatrix/reports').glob('*'))
            self.assertEqual(len(reports),1)
            self.assertTrue((reports[0]/'CREATRIX_DASHBOARD.html').exists())
            self.assertTrue((home/'.local/bin/genesis-creatrix-run').exists())
            parsed=json.loads((reports[0]/'CREATRIX_AUDIT.json').read_text())
            self.assertEqual(parsed['scope'],'CURRENT_LINUX_RUNTIME_ONLY')

    def test_safe_report_write_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'CREATRIX_AUDIT.json'
            p.write_text('owner data')
            with self.assertRaises(FileExistsError):
                quick._write_report_safely(p,'other data')
            self.assertEqual(p.read_text(),'owner data')

    def test_cpu_flags(self):
        self.assertEqual(quick.cpu_flags('flags : sse4_2 fma avx2 hypervisor\n'),['avx2','fma','sse4_2','hypervisor'])

    def test_swap_kind_redacts_path(self):
        output=quick.swap_devices('/dev/zram0 1G 2M 100\n/home/person/secrets.swap 2G 1M -2')
        self.assertEqual(output[0]['kind'],'ZRAM')
        self.assertEqual(output[1]['kind'],'SWAP_FILE')
        self.assertNotIn('secrets',str(output))

if __name__=='__main__':
    unittest.main()
