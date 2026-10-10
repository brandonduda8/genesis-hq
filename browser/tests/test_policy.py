import copy
import unittest

from genesis_browser.policy import RunOptions, PolicyError, read_plan, approval_check, digest, safe_origin
from genesis_browser.runner import execute


def basic(url='https://example.org', actions=None):
    return {'schema':'genesis-browser-plan/v1','job_id':'demo-01','allowed_origins':[url], 'actions':actions or [{'id':'a1','kind':'navigate','url':url}]}


class PolicyTests(unittest.TestCase):
    def rejected(self, p, **kwargs):
        with self.assertRaises(PolicyError): read_plan(p,**kwargs)

    def test_safe_external_origin(self):
        self.assertEqual(safe_origin('https://example.org/foo'),'https://example.org')

    def test_reject_http_external(self):
        with self.assertRaises(PolicyError):safe_origin('http://example.org')

    def test_reject_local_and_file(self):
        for x in ['http://127.0.0.1:8080', 'https://localhost', 'file:///etc/passwd', 'http://169.254.169.254/latest', 'https://127.0.0.1','https://10.0.0.1']:
            with self.subTest(x=x),self.assertRaises(PolicyError): safe_origin(x)

    def test_reject_url_credentials(self):
        with self.assertRaises(PolicyError):safe_origin('https://admin:secret@example.org')

    def test_local_fixture_opt_in(self):
        self.assertEqual(safe_origin('http://127.0.0.1:7777',allow_fixture=True),'http://127.0.0.1:7777')

    def test_fixture_does_not_allow_public_mutation(self):
        p=basic(actions=[{'id':'c','kind':'click','role':'button','name':'Create sample plan'}])
        self.rejected(p,fixture=True)

    def test_duplicate_id(self):
        p=basic(actions=[{'id':'a','kind':'screenshot'},{'id':'a','kind':'snapshot'}])
        self.rejected(p)

    def test_unknown_action_field(self):
        p=basic(actions=[{'id':'a','kind':'screenshot','execute_shell':'curl secrets'}]);self.rejected(p)

    def test_offdomain_navigation(self):
        p=basic(actions=[{'id':'a','kind':'navigate','url':'https://other.example'}]);self.rejected(p)

    def test_block_all_public_mutations(self):
        p=basic(actions=[{'id':'a','kind':'click','role':'button','name':'Save draft'}]);self.rejected(p)

    def test_sensitive_name_even_fixture(self):
        p=basic('http://127.0.0.1:7777',[{'id':'a','kind':'click','role':'button','name':'Pay now'}]);self.rejected(p,fixture=True)

    def test_fixture_authorization_exact_hash(self):
        p=basic('http://127.0.0.1:7777',[{'id':'a','kind':'fill','role':'textbox','name':'Project','value':'demo'}]);read_plan(p,fixture=True)
        a={'plan_sha256':digest(p),'approved_action_ids':['a'],'purpose':'LOCAL_FIXTURE_TEST_ONLY'}
        approval_check(p,a)
        with self.assertRaises(PolicyError):approval_check(p,{**a,'plan_sha256':'0'*64})
        with self.assertRaises(PolicyError):approval_check(p,{**a,'approved_action_ids':['x']})

    def test_local_fixture_mutation_needs_approval(self):
        p=basic('http://127.0.0.1:7777',[{'id':'a','kind':'fill','role':'textbox','name':'Project','value':'demo'}]);read_plan(p,fixture=True)
        with self.assertRaises(PolicyError):execute(p,'not-used',options=RunOptions(fixture=True,execute=True))

    def test_preflight_never_launches_browser(self):
        p=basic();r=execute(p,'/does/not/exist', options=RunOptions())
        self.assertEqual(r['execution'],'PREFLIGHT_ONLY')
        self.assertEqual(r['plan_sha256'],digest(p))

    def test_invalid_budget(self):
        with self.assertRaises(PolicyError): RunOptions(max_seconds=1000)

    def test_no_javascript_action(self):
        p=basic(actions=[{'id':'a','kind':'evaluate','code':'fetch("/secret")'}]);self.rejected(p)

    def test_invalid_scope_ip_literal(self):
        self.rejected(basic('https://192.168.1.7'))

    def test_invalid_repeated_origin(self):
        p=basic();p['allowed_origins']=['https://example.org','https://example.org'];self.rejected(p)


if __name__=='__main__': unittest.main()
