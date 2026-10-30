"""Hermetic tests: mocked Claude CLI; no network, real tokens, or live model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'claude-mission.py'


class ClaudeMissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.hq = self.root / 'hq'
        self.astra = self.root / 'astra'
        (self.hq / 'inbox').mkdir(parents=True)
        (self.hq / 'outbox').mkdir()
        (self.astra / 'shared/astra-workspace').mkdir(parents=True)
        (self.astra / 'shared/astra-os').mkdir(parents=True)
        (self.astra / 'shared/a2a-fabric').mkdir(parents=True)
        for path in ('AGENTS.md', 'CLAUDE.md', 'README.md',
                     'shared/astra-workspace/MASTER_DESIGN.md',
                     'shared/astra-os/ASTRA_BASE_FLAGSHIP_ARCHITECTURE.md',
                     'shared/a2a-fabric/ARCHITECTURE.md'):
            (self.astra / path).write_text('ASTRA source: ' + path)
        (self.astra / '.env').write_text('PRIVATE=DO_NOT_READ')
        self.wo = self.hq / 'inbox' / 'WO-ASTRA-001.txt'
        self.wo.write_text('Audit ASTRA source ownership and report blockers. Do not execute.')
        self.cli = self.root / 'claude'
        self.log = self.root / 'called.json'
        self.set_cli()

    def set_cli(self, auth=True, run=True, method='claude.ai'):
        # The fake CLI cannot use an env var to locate its log, since the runner
        # should scrub all unrelated caller environment variables.
        code = f'''#!/usr/bin/env python3
import json, os, pathlib, sys
argv=sys.argv[1:]
if argv[:2]==['auth','status']:
 print(json.dumps({{'authMethod':{method!r}}}))
 sys.exit({0 if auth else 1})
if '-p' in argv:
 pathlib.Path({str(self.log)!r}).write_text(json.dumps({{'argv':argv, 'cwd':os.getcwd(), 'env':dict(os.environ), 'staged':sorted(str(p.relative_to(pathlib.Path.cwd())) for p in pathlib.Path.cwd().rglob('*') if p.is_file())}}))
 print('Observed repo docs; BLOCKED until independent verification')
 sys.exit({0 if run else 1})
sys.exit(3)
'''
        self.cli.write_text(code)
        self.cli.chmod(0o700)

    def invoke(self, path=None, extra=None, env_add=None):
        env = os.environ.copy()
        env['HOME'] = str(self.root)
        env['OPENAI_API_KEY'] = 'SHOULD_NEVER_BE_IN_WORKER_ENV'
        env.update(env_add or {})
        args = [sys.executable, str(SCRIPT), str(path or self.wo), '--hq-root', str(self.hq),
                '--astra-root', str(self.astra), '--claude-bin', str(self.cli), '--timeout', '4']
        return subprocess.run(args + (extra or []), capture_output=True, text=True, env=env, timeout=8)

    def test_real_flow_creates_claimed_report_and_receipt(self):
        r = self.invoke()
        self.assertEqual(r.returncode, 0, r.stderr)
        receipt = json.loads((self.hq / 'outbox/WO-ASTRA-001.claude-receipt.json').read_text())
        self.assertEqual(receipt['state'], 'DELIVERED_UNVERIFIED')
        self.assertEqual(receipt['verification'], 'NOT_INDEPENDENTLY_VERIFIED')
        self.assertTrue((self.hq / 'outbox/WO-ASTRA-001.claude-report.md').is_file())
        self.assertEqual(len(receipt['files_staged']), 6)

    def test_no_shell_write_network_or_external_mcp(self):
        self.assertEqual(self.invoke().returncode, 0)
        log = json.loads(self.log.read_text())
        self.assertIn('--restricted', log['argv'])
        self.assertIn('dontAsk', log['argv'])
        self.assertIn('Read,Glob,Grep', log['argv'])
        self.assertIn('mcp__*', log['argv'])
        self.assertNotIn('OPENAI_API_KEY', log['env'])
        self.assertNotIn('ANTHROPIC_API_KEY', log['env'])
        self.assertNotIn('.env', log['staged'])
        self.assertEqual(len(log['staged']), 6)

    def test_missing_auth_blocks(self):
        self.set_cli(auth=False)
        r = self.invoke()
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_api_key_authentication_is_blocked(self):
        self.set_cli(method='api_key')
        self.assertEqual(self.invoke().returncode, 2)
        self.assertFalse(self.log.exists())

    def test_symlink_order_refused(self):
        other = self.root / 'external.txt'
        other.write_text('hi')
        self.wo.unlink()
        self.wo.symlink_to(other)
        self.assertEqual(self.invoke().returncode, 2)

    def test_outside_inbox_refused(self):
        external = self.root / 'WO-ASTRA-001.txt'
        external.write_text('hi')
        self.assertEqual(self.invoke(path=external).returncode, 2)

    def test_replay_blocked(self):
        self.assertEqual(self.invoke().returncode, 0)
        self.assertEqual(self.invoke().returncode, 2)
        self.assertIn('already used', self.invoke().stderr)

    def test_failed_model_is_never_verified(self):
        self.set_cli(run=False)
        self.assertEqual(self.invoke().returncode, 1)
        receipt = json.loads((self.hq / 'outbox/WO-ASTRA-001.claude-receipt.json').read_text())
        self.assertEqual(receipt['state'], 'FAILED_UNVERIFIED')
        self.assertFalse((self.hq / 'outbox/WO-ASTRA-001.claude-report.md').exists())

    def test_rejects_secret_in_work_order(self):
        self.wo.write_text('credential: ' + 'ghp_' + 'A' * 30)
        self.assertEqual(self.invoke().returncode, 2)
        self.assertFalse(self.log.exists())

    def test_outbox_report_symlink_is_not_overwritten(self):
        target = self.root / 'victim'
        target.write_text('unchanged')
        report = self.hq / 'outbox' / 'WO-ASTRA-001.claude-report.md'
        report.symlink_to(target)
        self.assertEqual(self.invoke().returncode, 2)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_lock_symlink_is_refused(self):
        target = self.root / 'victim'
        target.write_text('unchanged')
        (self.hq / 'outbox' / '.claude-mission.lock').symlink_to(target)
        self.assertEqual(self.invoke().returncode, 2)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_rejects_large_work_order(self):
        self.wo.write_text('A' * 4097)
        self.assertEqual(self.invoke().returncode, 2)


if __name__ == '__main__':
    unittest.main()
