import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from creatrix import audit
from creatrix.compare import comparison


class ParsingTests(unittest.TestCase):
    def test_mem(self):
        self.assertEqual(audit.meminfo('MemTotal: 2700000 kB\nMemAvailable: 1000000 kB\nSecrets: 4 kB'),
                         {'MemTotal': 2700000 * 1024, 'MemAvailable': 1000000 * 1024})

    def test_mem_bad_ignored(self):
        self.assertEqual(audit.meminfo('MemTotal: -3 kB\nMemAvailable: abc\n'), {})

    def test_mem_blank(self):
        self.assertEqual(audit.meminfo(''), {})

    def test_cgroup_max(self):
        self.assertIsNone(audit.cgroup_bytes('max'))

    def test_cgroup_int(self):
        self.assertEqual(audit.cgroup_bytes('4000\n'), 4000)

    def test_cgroup_bad(self):
        self.assertIsNone(audit.cgroup_bytes('-1'))

    def test_events(self):
        self.assertEqual(audit.cgroup_events('low 1\nhi 6\noom_kill 8\n'), {'low': 1, 'oom_kill': 8})

    def test_pressure(self):
        self.assertEqual(audit.pressure('some avg10=2.0 avg60=0.3 total=88\nfull avg10=0.0'),
                         {'some': {'avg10': 2.0, 'avg60': 0.3}, 'full': {'avg10': 0.0}})

    def test_cpu(self):
        self.assertEqual(audit.cpu_name('processor: 0\nmodel name : Intel test CPU\n'), 'Intel test CPU')

    def test_cpu_unknown(self):
        self.assertEqual(audit.cpu_name(''), 'UNKNOWN')

    def test_osrelease(self):
        self.assertEqual(audit.os_release('ID=debian\nNAME=secret\nVERSION_ID="13"\n'),
                         {'ID': 'debian', 'VERSION_ID': '13'})

    def test_processes_names_only(self):
        self.assertEqual(audit.process_rss('bash 64\nopenclaw 730000\nnode 300000\n'),
                         [{'process': 'openclaw', 'rss_kib': 730000},
                          {'process': 'node', 'rss_kib': 300000}, {'process': 'bash', 'rss_kib': 64}])

    def test_processes_reject_command_arguments(self):
        self.assertEqual(audit.process_rss('node --api-token=supersecret 1234\n'), [])

    def test_ports(self):
        self.assertEqual(audit.listening_ports('LISTEN 0 4096 127.0.0.1:11434 0.0.0.0:*\nLISTEN 0 4 *:22 *:*\n'), [22, 11434])

    def test_ports_private_other_absent(self):
        self.assertEqual(audit.listening_ports('LISTEN 0 3 0.0.0.0:55555 0.0.0.0:*'), [])

    def test_gpu_names(self):
        self.assertEqual(audit.gpu_names('00:02.0 VGA compatible controller: Intel Test GPU\n00:04.0 Network controller: Wifi\n'), ['Intel Test GPU'])


class GovernorTests(unittest.TestCase):
    def test_critical_low(self):
        m = {'MemTotal': 2 * 1024**3, 'MemAvailable': 300 * 1024**2}
        a = audit.capacity_plan(m, None)
        self.assertEqual(a['state'], 'CRITICAL')
        self.assertEqual(a['proposed_worker_rss_cap_bytes'], 0)

    def test_constrained(self):
        m = {'MemTotal': 3 * 1024**3, 'MemAvailable': 1100 * 1024**2}
        self.assertEqual(audit.capacity_plan(m, None)['state'], 'CONSTRAINED')

    def test_available(self):
        m = {'MemTotal': 4 * 1024**3, 'MemAvailable': 2700 * 1024**2}
        a = audit.capacity_plan(m, None)
        self.assertEqual(a['state'], 'AVAILABLE_FOR_ONE_BOUNDED_WORKER')
        self.assertLessEqual(a['proposed_worker_rss_cap_bytes'], 700 * 1024**2)

    def test_unknown(self):
        self.assertEqual(audit.capacity_plan({}, None)['state'], 'UNKNOWN')

    def test_mem_cgroup_clamp(self):
        m = {'MemTotal': 8 * 1024**3, 'MemAvailable': 5 * 1024**3}
        a = audit.capacity_plan(m, 3 * 1024**3)
        self.assertEqual(a['reserve_bytes'], int(3 * 1024**3 * .28))

    def test_one_slot(self):
        self.assertTrue(audit.capacity_plan({'MemTotal': 2**30, 'MemAvailable': 2**29}, None)['one_heavy_worker_max'])


class OutputTests(unittest.TestCase):
    def fixture(self):
        return {
            'schema': 'genesis-creatrix-audit/1', 'collected_utc': '2026-10-26T10:00:00Z',
            'reported_device_label': 'penguin', 'scope': 'CURRENT_LINUX_RUNTIME_ONLY',
            'hardware_board_prior_user_report': 'ELEMI', 'os': {'PRETTY_NAME': 'Debian GNU/Linux 13'},
            'kernel': '6.6', 'cpu': {'model': 'Intel i3', 'logical_processors': 4},
            'memory': {'MemTotal': 3*1024**3, 'MemAvailable': 2*1024**3},
            'cgroup': {'memory_limit_bytes': 4*1024**3, 'memory_events': {'oom_kill': 0},
                       'memory_pressure': {'some': {'avg10': 0.0}}},
            'disk_guest_root': {'total_bytes': 32*1024**3, 'free_bytes': 20*1024**3},
            'tools_available': {'ssh': True}, 'services': {'ssh': 'active'},
            'ports_listening_selected_only': [22],
            'top_processes_rss_only': [{'process': 'node', 'rss_kib': 200000}],
            'admission_plan': audit.capacity_plan({'MemTotal': 3*1024**3, 'MemAvailable': 2*1024**3}, 4*1024**3)
        }

    def test_render(self):
        self.assertIn('ChromeOS host storage: UNKNOWN', audit.render(self.fixture()))

    def test_render_no_secret(self):
        self.assertNotIn('api-token', audit.render(self.fixture()))

    def test_compare_same(self):
        self.assertEqual(comparison(self.fixture(), self.fixture())['memory_delta_bytes']['MemTotal'], 0)

    def test_compare_added_mem(self):
        a = self.fixture(); b = json.loads(json.dumps(a)); b['memory']['MemAvailable'] += 1000
        self.assertEqual(comparison(a, b)['memory_delta_bytes']['MemAvailable'], 1000)

    def test_compare_wrong_schema(self):
        a = self.fixture(); a['schema'] = 'evil'
        with self.assertRaises(ValueError):
            comparison(a, self.fixture())

    def test_no_network_default(self):
        with patch('creatrix.audit.subprocess.run') as mocked:
            with patch('creatrix.audit.shutil.which', return_value='/usr/bin/ps'):
                audit.call(['ps', '-eo', 'comm,rss'])
                args = mocked.call_args.args[0]
                self.assertEqual(args[0], 'ps')

    def test_cli_files(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('creatrix.audit.collect', return_value=self.fixture()):
                result = audit.main(['--out', d, '--label', 'penguin'])
                self.assertEqual(result, 0)
                self.assertTrue((Path(d) / 'CREATRIX_AUDIT.json').exists())
                self.assertTrue((Path(d) / 'CREATRIX_AUDIT.md').exists())
                self.assertTrue((Path(d) / 'SHA256.txt').exists())


if __name__ == '__main__':
    unittest.main()
