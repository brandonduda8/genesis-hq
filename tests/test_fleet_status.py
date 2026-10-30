"""Hermetic read-only checks for the fleet observer (does not start agents)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'fleet-status.sh'


class FleetStatusTests(unittest.TestCase):
    def invoke(self, home, *args, overrides=None):
        env = dict(os.environ, HOME=str(home))
        env['GENESIS_AGENT_X_ROOT'] = str(home / 'agent-x')
        env['GENESIS_CORE_ROOT'] = str(home / 'genesis-core')
        env['GENESIS_MAILBOX_ROOT'] = str(home / 'mailbox')
        if overrides:
            env.update(overrides)
        return subprocess.run(['bash', str(SCRIPT), *args], env=env,
                              capture_output=True, text=True, timeout=5)

    def test_missing_is_not_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.invoke(Path(tmp), '--json')
            self.assertEqual(p.returncode, 0, p.stderr)
            j = json.loads(p.stdout)
            self.assertEqual(j['authority'], 'observation-only')
            states = {w['id']: w['state'] for w in j['workers']}
            self.assertEqual(states['agent_x'], 'NOT_OBSERVED')
            self.assertEqual(states['starnet'], 'NOT_OBSERVED')
            self.assertEqual(states['prime'], 'UNMAPPED')
            self.assertTrue(all('READY' != w['state'] for w in j['workers']))

    def test_marker_does_not_imply_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'agent-x' / 'cody-core' / 'codycore' / 'starnet.py'
            marker.parent.mkdir(parents=True)
            marker.write_text('')
            result = self.invoke(root, '--json')
            states = {w['id']: w['state'] for w in json.loads(result.stdout)['workers']}
            self.assertEqual(states['starnet'], 'ADAPTER_CODE_ONLY')
            self.assertEqual(states['agent_x'], 'NOT_OBSERVED')

    def test_symlink_marker_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'target'
            target.write_text('')
            marker = root / 'agent-x' / 'cody-core' / 'codycore' / 'starnet.py'
            marker.parent.mkdir(parents=True)
            marker.symlink_to(target)
            result = self.invoke(root, '--json')
            states = {w['id']: w['state'] for w in json.loads(result.stdout)['workers']}
            self.assertEqual(states['starnet'], 'NOT_OBSERVED')

    def test_rejects_unknown_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.invoke(Path(tmp), '--execute').returncode, 2)
            self.assertEqual(self.invoke(Path(tmp), '--json', 'extra').returncode, 2)

    def test_text_output_has_no_secrets_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.invoke(Path(tmp), overrides={'OPENAI_API_KEY': 'very_sensitive_test_value'})
            self.assertEqual(result.returncode, 0)
            self.assertIn('worker=starnet state=NOT_OBSERVED', result.stdout)
            self.assertNotIn('very_sensitive_test_value', result.stdout)


if __name__ == '__main__':
    unittest.main()
