import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cody_backup as c

class FakeHTTP:
    def __init__(self, status): self.status=status
    def __enter__(self): return self
    def __exit__(self,*_): return False


class StandbyTests(unittest.TestCase):
    def test_https_origin_restriction(self):
        self.assertEqual(c.safe_render_url(c.DEFAULT_RENDER),c.DEFAULT_RENDER)
        for url in ('http://example.com','https://example.com/x','https://user:pass@example.com',
                    'https://example.com?token=x'):
            with self.assertRaises(ValueError): c.safe_render_url(url)

    def test_model_probe_restricts_loopback(self):
        self.assertIsNone(c.probe_model(None))
        for url in ('https://example.com','http://attacker.example:1234','http://localhost:11434?key=1'):
            with self.assertRaises(ValueError): c.safe_local_model_url(url)
        self.assertEqual(c.safe_local_model_url('http://127.0.0.1:11434/api/tags'),
                         'http://127.0.0.1:11434/api/tags')

    def test_no_node_secret_never_transmits(self):
        payload=c.sanitize_observation(github=True,model=None,boot_id='c'*32,seq=1)
        with patch.object(c,'urlopen') as u:
            self.assertEqual(c.post_observation(c.DEFAULT_RENDER,None,payload),'BLOCKED_CREDENTIALS')
            u.assert_not_called()

    def test_github_probe_reports_http_status_as_reachable(self):
        with patch.object(c,'urlopen',side_effect=HTTPError(c.GITHUB_PROBE,403,'forbidden',{},None)):
            self.assertTrue(c.probe_github())
        with patch.object(c,'urlopen',side_effect=URLError('timeout')):
            self.assertFalse(c.probe_github())

    def test_publish_distinguishes_transport_and_authorization(self):
        payload=c.sanitize_observation(github=True,model=None,boot_id='c'*32,seq=1)
        with patch.object(c,'urlopen',return_value=FakeHTTP(202)):
            self.assertEqual(c.post_observation(c.DEFAULT_RENDER,'x'*40,payload),'RENDER_OBSERVED')
        with patch.object(c,'urlopen',side_effect=HTTPError(c.DEFAULT_RENDER,401,'no',{},None)):
            self.assertEqual(c.post_observation(c.DEFAULT_RENDER,'x'*40,payload),'BLOCKED_CREDENTIALS')
        with patch.object(c,'urlopen',side_effect=URLError('private provider URL and secret')):
            self.assertEqual(c.post_observation(c.DEFAULT_RENDER,'x'*40,payload),'BLOCKED_EGRESS')

    def test_sequential_observations_persist_without_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            events=[]
            def publish(server,token,pulse):
                events.append(pulse)
                return 'RENDER_OBSERVED'
            for _ in range(2):
                out=c.run_once(state_dir=Path(td)/'state',github_probe=lambda:True,
                   model_probe=lambda u:None,publisher=publish,token='x'*40)
                self.assertEqual(out['render_delivery'],'RENDER_OBSERVED')
                self.assertEqual(out['execution'],'NOT_ENABLED')
            self.assertEqual([p['seq'] for p in events],[1,2]);self.assertEqual(events[0]['boot_id'],events[1]['boot_id'])
            data=(Path(td)/'state/watch.json').read_text();self.assertNotIn('x'*40,data)
            self.assertEqual((Path(td)/'state').stat().st_mode & 0o777,0o700)

    def test_corrupt_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'watch.json').write_text('{invalid')
            with self.assertRaises(ValueError):c.run_once(state_dir=root,github_probe=lambda:True,model_probe=lambda x:None)

    def test_no_model_is_not_ready_and_network_failure_is_distinct(self):
        obj=c.sanitize_observation(github=True,model=None,boot_id='a'*32,seq=1)
        self.assertEqual(obj['state'],'MODEL_MISSING');self.assertEqual(obj['capabilities'],['probe','receipt'])
        blocked=c.sanitize_observation(github=False,model=None,boot_id='a'*32,seq=1)
        self.assertEqual(blocked['state'],'BLOCKED_EGRESS')
        observed=c.sanitize_observation(github=True,model=True,boot_id='a'*32,seq=1)
        self.assertEqual(observed['state'],'MODEL_ENDPOINT_OBSERVED')

    def test_doctor_without_key_explains_requirement(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(c.main(['doctor']),0)

if __name__=='__main__':unittest.main()
