import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap

SOURCE = Path(__file__).resolve().parents[1]

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.fetcher=lambda name,sha:(SOURCE/name).read_bytes()
        self.p1=patch.object(bootstrap,'_fetch',side_effect=self.fetcher)
        self.p2=patch.object(bootstrap,'_validate_user',return_value=None)
        self.p1.start();self.p2.start()
    def tearDown(self):
        self.p1.stop();self.p2.stop();self.tmp.cleanup()
    def test_manifest_source_hashes_match(self):
        for name,sha in bootstrap.MANIFEST.items():
            self.assertEqual(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest(),sha)
    def test_install_and_recheck(self):
        app=bootstrap.install(self.home)
        self.assertTrue((app/'creatrix_station.py').is_file())
        self.assertTrue((app/'factory_mcp.py').is_file())
        self.assertEqual(bootstrap.install(self.home),app)
        self.assertTrue((self.home/'.local/bin/creatrix').exists())
    def test_partial_fetch_rolls_back_no_launcher(self):
        def fail(name,sha):
            if name=='codyctl.py':raise OSError('Simulated offline')
            return (SOURCE/name).read_bytes()
        with patch.object(bootstrap,'_fetch',side_effect=fail):
            with self.assertRaises(OSError):bootstrap.install(self.home)
        self.assertFalse((self.home/'.local/bin/creatrix').exists())
        self.assertFalse((self.home/'.local/share/genesis-creatrix/releases/creatrix-v1.1.0').exists())
    def test_modified_existing_release_no_overwrite(self):
        app=bootstrap.install(self.home)
        (app/'codyctl.py').write_text('tampered')
        with self.assertRaises(RuntimeError):bootstrap.install(self.home)
        self.assertEqual((app/'codyctl.py').read_text(),'tampered')
    def test_conflicting_launcher_no_overwrite(self):
        self.home.joinpath('.local/bin').mkdir(parents=True)
        (self.home/'.local/bin/creatrix').write_text('#!/bin/sh\necho existing\n')
        with self.assertRaises(RuntimeError):bootstrap.install(self.home)
        self.assertEqual((self.home/'.local/bin/creatrix').read_text(),'#!/bin/sh\necho existing\n')
    def test_symlinked_share_denied(self):
        self.home.joinpath('.local').mkdir()
        (self.home/'.local/share').symlink_to(self.home)
        with self.assertRaises(RuntimeError):bootstrap.install(self.home)

if __name__=='__main__':unittest.main()
