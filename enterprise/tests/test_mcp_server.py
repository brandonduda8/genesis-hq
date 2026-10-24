"""Standard library fixture tests for demo-only MCP tools (no providers)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mcp_server import Drafts, call, rpc, TOOLS

class EnterpriseMCPTests(unittest.TestCase):
    def setUp(self):
        self.d=Drafts()
    def test_exact_tool_set_is_safe(self):
        assert "pay.execute" not in TOOLS
        assert "outreach.send" not in TOOLS
        assert "compute.execute" not in TOOLS
        assert "pay.invoice_draft" in TOOLS
    def test_status_denies_financial_and_outreach(self):
        s=call("system.status",{},self.d)
        self.assertFalse(s["live_payments"])
        self.assertFalse(s["outreach_enabled"])
        self.assertEqual(s["real_income_verified_cents"],0)
    def test_contract_not_verified(self):
        p=call("contracts.qualify",{"title":"Audit","source_url":"https://example.org/bid",
             "budget_cents":30000,"fit_percent":85},self.d)
        self.assertFalse(p["listing_verified"])
    def test_proposal_not_sent(self):
        p=call("contracts.draft_proposal",{"title":"Audit","scope":"One report","price_cents":40000},self.d)
        self.assertFalse(p["send_authorized"])
    def test_computing_never_claims_remote_gpu(self):
        p=call("compute.plan",{"workload":"training","estimated_ram_mib":8000,"requires_gpu":True},self.d)
        self.assertFalse(p["actual_gpu_allocated"])
        self.assertIsNone(p["worker"])
    def test_invoice_never_pays(self):
        a={"client_alias":"fictional-client","purpose":"Demo audit","amount_cents":4900,
           "currency":"USD","idempotency_key":"id1"}
        p=call("pay.invoice_draft",a,self.d)
        self.assertFalse(p["money_moved"])
        self.assertFalse(p["verified_payment"])
    def test_repeat_invoice_is_idempotent(self):
        a={"client_alias":"fictional-client","purpose":"Demo audit","amount_cents":4900,
           "currency":"USD","idempotency_key":"id1"}
        x=call("pay.invoice_draft",a,self.d)
        y=call("pay.invoice_draft",a,self.d)
        self.assertEqual(x["ref"],y["ref"])
        self.assertTrue(y["duplicate"])
    def test_tamper_invoice_is_rejected(self):
        a={"client_alias":"fictional-client","purpose":"Demo audit","amount_cents":4900,
           "currency":"USD","idempotency_key":"id1"}
        call("pay.invoice_draft",a,self.d)
        with self.assertRaisesRegex(ValueError,"IDEMPOTENCY_CONFLICT"):
            call("pay.invoice_draft",{**a,"amount_cents":9900},self.d)
    def test_spend_not_authorized(self):
        a={"agent_id":"cody","merchant_alias":"demo-provider","purpose":"Synthetic compute","amount_cents":125,
           "currency":"USD","idempotency_key":"s1"}
        p=call("pay.spend_request",a,self.d)
        self.assertEqual(p["authorized_spend_cents"],0)
        self.assertFalse(p["money_moved"])
    def test_duplicate_same_id_cross_type_rejected(self):
        call("pay.invoice_draft",{"client_alias":"fictional","purpose":"Demo","amount_cents":50,
            "currency":"USD","idempotency_key":"shared"},self.d)
        with self.assertRaisesRegex(ValueError,"IDEMPOTENCY_CONFLICT"):
            call("pay.spend_request",{"agent_id":"cody","merchant_alias":"x","purpose":"test",
                 "amount_cents":50,"currency":"USD","idempotency_key":"shared"},self.d)
    def test_float_and_boolean_are_not_money(self):
        for x in (1.5,True,False,-1,0):
            with self.assertRaises(ValueError):
                call("pay.invoice_draft",{"client_alias":"fake","purpose":"test","amount_cents":x,
                     "currency":"USD","idempotency_key":"i"},self.d)
    def test_wrong_currency_denied(self):
        with self.assertRaises(ValueError):
            call("pay.invoice_draft",{"client_alias":"fake","purpose":"test","amount_cents":50,
                 "currency":"EUR","idempotency_key":"i"},self.d)
    def test_extra_fields_denied_and_secrets_not_echoed(self):
        m={"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"pay.invoice_draft",
           "arguments":{"client_alias":"x","purpose":"x","amount_cents":50,"currency":"USD",
                        "idempotency_key":"i","api_key":"SUPERSECRET"}}}
        out=rpc(m,self.d)
        self.assertTrue(out["result"]["isError"])
        self.assertNotIn("SUPERSECRET",json.dumps(out))
    def test_notifications_never_do_work(self):
        n={"jsonrpc":"2.0","method":"tools/call","params":{"name":"pay.spend_request","arguments":{}}}
        self.assertIsNone(rpc(n,self.d))
    def test_protocol_stdio(self):
        req=[{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"fixture","version":"1"}}},
             {"jsonrpc":"2.0","id":2,"method":"tools/list"},
             {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"system.status","arguments":{}}}]
        run=subprocess.run([sys.executable,str(ROOT/"mcp_server.py")],
             input="".join(json.dumps(m)+"\n" for m in req),text=True,capture_output=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)
        got=[json.loads(x) for x in run.stdout.splitlines()]
        self.assertEqual(len(got),3)
        self.assertEqual(got[0]["result"]["serverInfo"]["name"],"genesis-enterprise-mcp-demo")
        self.assertEqual(len(got[1]["result"]["tools"]),6)
        self.assertIn("LOCAL_DEMO_ONLY",got[2]["result"]["content"][0]["text"])

if __name__=="__main__": unittest.main()
