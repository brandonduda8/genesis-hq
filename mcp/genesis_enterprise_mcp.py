#!/usr/bin/env python3
"""Genesis Enterprise MCP v0.1: sandbox-only drafts, no external effects.

Stdio JSON-RPC transport. DOES NOT send outreach, authorize money, process
payments, execute cloud jobs, use API keys or access networks. The transport
trusts its local launching process; not suitable for untrusted remote clients.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

MAX_LINE = 65536
MAX_TEXT = 240
IDPAT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


def _text(x, field, limit=MAX_TEXT):
    if not isinstance(x, str) or not x.strip() or len(x) > limit or any(ord(c) < 32 for c in x):
        raise ValueError("INVALID_" + field.upper())
    return x.strip()


def _money(x, field="amount_cents", allow_zero=False):
    if isinstance(x, bool) or not isinstance(x, int) or not (0 if allow_zero else 1) <= x <= 100000000:
        raise ValueError("INVALID_" + field.upper())
    return x


def _keys(args, required, optional=()):
    if not isinstance(args, dict) or set(args) - set(required) - set(optional) or set(required) - set(args):
        raise ValueError("INVALID_ARGUMENTS")


def _iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DraftStore:
    """Not a financial ledger. Stores NON-AUTHORIZING drafts; never records income."""
    def __init__(self, path=":memory:"):
        if not isinstance(path, str) or not path:
            raise ValueError("INVALID_DB_PATH")
        if path != ":memory:":
            # Open private files only. Caller secures containing directory.
            os.umask(0o077)
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.execute("PRAGMA busy_timeout=5000")
        if path != ":memory:":
            self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS drafts(
            ref TEXT PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL,
            idem TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
            payload TEXT NOT NULL, created_utc TEXT NOT NULL)""")

    def put(self, kind, idem, payload, state):
        idem = _text(idem, "idempotency_key", 80)
        if not IDPAT.fullmatch(idem):
            raise ValueError("INVALID_IDEMPOTENCY_KEY")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256((kind + "\0" + raw).encode()).hexdigest()
        ref = "draft-" + hashlib.sha256((kind + "\0" + idem).encode()).hexdigest()[:24]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT kind,fingerprint,ref,state FROM drafts WHERE idem=?", (idem,)).fetchone()
            if existing:
                if existing[0] != kind or existing[1] != digest:
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                result = {"ref": existing[2], "state": existing[3], "duplicate": True}
            else:
                self.db.execute("INSERT INTO drafts VALUES (?,?,?,?,?,?,?)",
                                (ref, kind, state, idem, digest, raw, _iso_now()))
                result = {"ref": ref, "state": state, "duplicate": False}
            self.db.execute("COMMIT")
            return result
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def get(self, ref):
        ref = _text(ref, "ref", 80)
        if not ref.startswith("draft-") or not IDPAT.fullmatch(ref):
            raise ValueError("INVALID_REF")
        row = self.db.execute("SELECT kind,state,created_utc,payload FROM drafts WHERE ref=?", (ref,)).fetchone()
        if not row:
            return {"state": "NOT_FOUND", "ref": ref}
        return {"ref": ref, "kind": row[0], "state": row[1], "created_utc": row[2], "payload": json.loads(row[3]),
                "payment_provider_receipt": None, "verified_revenue_cents": 0}


def score_opportunity(args):
    _keys(args, ("title", "source_url", "budget_cents", "fit_percent", "submission_fee_cents"))
    title = _text(args["title"], "title")
    url = _text(args["source_url"], "source_url", 500)
    if not url.startswith("https://") or any(c in url for c in "@ #\\"):
        raise ValueError("INVALID_SOURCE_URL")
    budget = _money(args["budget_cents"], "budget_cents")
    fee = _money(args["submission_fee_cents"], "submission_fee_cents", True)
    fit = args["fit_percent"]
    if isinstance(fit, bool) or not isinstance(fit, int) or fit not in range(0, 101):
        raise ValueError("INVALID_FIT_PERCENT")
    return {"state": "UNVERIFIED_OPPORTUNITY_ESTIMATE", "title": title, "source_url": url,
            "score": max(0, min(100, fit - (20 if fee else 0))), "estimated_budget_cents": budget,
            "submission_fee_cents": fee, "listing_verified": False, "submission_authorized": False,
            "requires": ["live_listing_check", "eligibility", "delivery_cost_review", "owner_submit_approval"]}


def draft_proposal(args):
    _keys(args, ("opportunity_title", "deliverable", "milestones", "price_cents"))
    title = _text(args["opportunity_title"], "opportunity_title")
    deliverable = _text(args["deliverable"], "deliverable", 500)
    milestones = args["milestones"]
    if not isinstance(milestones, list) or not 1 <= len(milestones) <= 5:
        raise ValueError("INVALID_MILESTONES")
    milestones = [_text(s, "milestone") for s in milestones]
    price = _money(args["price_cents"], "price_cents")
    return {"state": "DRAFT_ONLY_NOT_SENT", "opportunity_title": title, "proposal": {
        "scope": deliverable, "milestones": milestones, "price_cents": price, "currency": "USD",
        "claims": "No unverified credentials, customer results, availability or guaranteed ROI.",
        "terms": "Subject to independent QA, owner review, customer acceptance and written agreement."},
        "submit_capability": False}


def plan_compute(args):
    _keys(args, ("task_type", "estimated_ram_mib", "requires_gpu", "verified_nodes"))
    task = _text(args["task_type"], "task_type")
    ram = args["estimated_ram_mib"]
    if isinstance(ram, bool) or not isinstance(ram, int) or ram < 1 or ram > 1000000 or not isinstance(args["requires_gpu"], bool):
        raise ValueError("INVALID_RESOURCE_REQUEST")
    nodes = args["verified_nodes"]
    if not isinstance(nodes, list) or len(nodes) > 20:
        raise ValueError("INVALID_NODES")
    # Deliberately never convert self-reported telemetry to trusted capacity.
    return {"state": "PLAN_ONLY_UNVERIFIED_ATTESTATIONS", "task_type": task,
            "estimated_ram_mib": ram, "requires_gpu": args["requires_gpu"],
            "offered_nodes": len(nodes), "selected_node": None, "cloud_calls": 0,
            "required_next": "Authenticated and fresh independent host/quota attestations plus canonical ledger lease"}


def pay_preview(args):
    _keys(args, ("agent_id", "merchant_alias", "purpose", "amount_cents", "currency"))
    agent = _text(args["agent_id"], "agent_id", 80)
    merchant = _text(args["merchant_alias"], "merchant_alias")
    purpose = _text(args["purpose"], "purpose", 500)
    amount = _money(args["amount_cents"])
    if args["currency"] != "USD":
        raise ValueError("UNSUPPORTED_CURRENCY")
    return {"state": "NEEDS_TRUSTED_OWNER_AUTHORIZATION", "agent_id": agent,
            "merchant_alias": merchant, "purpose": purpose, "amount_cents": amount, "currency": "USD",
            "authorized_spend_cents": 0, "spend_executed": False,
            "requirements": ["trusted_signed_mandate", "verified_merchant", "merchant_and_amount_binding",
                             "server_side_budget", "independent_risk_check", "licensed_provider", "idempotency_and_receipt"]}


class EnterpriseTools:
    def __init__(self, store=None):
        self.store = store or DraftStore()

    def call(self, name, args):
        if name == "contracts.score":
            return score_opportunity(args)
        if name == "contracts.proposal_draft":
            return draft_proposal(args)
        if name == "compute.plan":
            return plan_compute(args)
        if name == "pay.preview_spend":
            return pay_preview(args)
        if name == "pay.invoice_draft":
            _keys(args, ("client_alias", "description", "amount_cents", "currency", "idempotency_key"))
            if args["currency"] != "USD":
                raise ValueError("UNSUPPORTED_CURRENCY")
            p = {"client_alias": _text(args["client_alias"], "client_alias"),
                 "description": _text(args["description"], "description", 500),
                 "amount_cents": _money(args["amount_cents"]), "currency": "USD"}
            return {**self.store.put("invoice", args["idempotency_key"], p, "DRAFT_NOT_ISSUED"),
                    "provider_payment_id": None, "payment_link": None, "verified_revenue_cents": 0}
        if name == "pay.authorization_request":
            _keys(args, ("agent_id", "merchant_alias", "purpose", "amount_cents", "currency", "idempotency_key"))
            p = pay_preview({key: args[key] for key in ("agent_id", "merchant_alias", "purpose", "amount_cents", "currency")})
            if p["authorized_spend_cents"] != 0:
                raise ValueError("AUTHORIZATION_MUST_BE_EXTERNAL")
            safe_payload = {k: p[k] for k in ("agent_id", "merchant_alias", "purpose", "amount_cents", "currency")}
            return {**self.store.put("payment_intent", args["idempotency_key"], safe_payload, "AWAITING_OWNER_REVIEW"),
                    "authorized_spend_cents": 0, "funds_moved": False}
        if name == "draft.get":
            _keys(args, ("ref",))
            return self.store.get(args["ref"])
        if name == "system.status":
            _keys(args, ())
            return {"status": "LOCAL_DEMO_ONLY", "provider_connections": 0, "real_payment_tools": 0,
                    "outreach_send_tools": 0, "cloud_execution_tools": 0,
                    "ledger": "NOT_CONNECTED_TO_GENESIS_CANONICAL_LEDGER", "claims_verified": False}
        raise ValueError("UNKNOWN_TOOL")


def _tool(name, description, properties, required):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties,
                            "required": required, "additionalProperties": False}}


def _str(): return {"type": "string", "maxLength": 500}

def _int(): return {"type": "integer", "minimum": 0, "maximum": 100000000}


def tool_catalog():
    s, i = _str(), _int()
    return [
        _tool("contracts.score", "Assess an UNVERIFIED contract lead from caller-supplied data; no live verification.",
              {"title":s,"source_url":s,"budget_cents":i,"fit_percent":i,"submission_fee_cents":i},
              ["title","source_url","budget_cents","fit_percent","submission_fee_cents"]),
        _tool("contracts.proposal_draft", "Create a proposal draft; NEVER sends or claims acceptance.",
              {"opportunity_title":s,"deliverable":s,"milestones":{"type":"array","items":s,"minItems":1,"maxItems":5},"price_cents":i},
              ["opportunity_title","deliverable","milestones","price_cents"]),
        _tool("compute.plan", "Return a resource planning placeholder, not authenticated worker admission.",
              {"task_type":s,"estimated_ram_mib":i,"requires_gpu":{"type":"boolean"},"verified_nodes":{"type":"array","maxItems":20,"items":{"type":"object"}}},
              ["task_type","estimated_ram_mib","requires_gpu","verified_nodes"]),
        _tool("pay.preview_spend", "Read-only spending policy requirements; never pays.",
              {"agent_id":s,"merchant_alias":s,"purpose":s,"amount_cents":i,"currency":{"type":"string","enum":["USD"]}},
              ["agent_id","merchant_alias","purpose","amount_cents","currency"]),
        _tool("pay.invoice_draft", "Create only an unissued invoice draft, with durable optional local storage.",
              {"client_alias":s,"description":s,"amount_cents":i,"currency":{"type":"string","enum":["USD"]},"idempotency_key":s},
              ["client_alias","description","amount_cents","currency","idempotency_key"]),
        _tool("pay.authorization_request", "Create only an owner-review request; cannot approve or transfer money.",
              {"agent_id":s,"merchant_alias":s,"purpose":s,"amount_cents":i,"currency":{"type":"string","enum":["USD"]},"idempotency_key":s},
              ["agent_id","merchant_alias","purpose","amount_cents","currency","idempotency_key"]),
        _tool("draft.get", "Read an existing LOCAL draft; requires trusted single-owner stdio host.",
              {"ref":s}, ["ref"]),
        _tool("system.status", "Report truthful capabilities; never imply live agents or finances.", {}, [])
    ]


def dispatch(msg, tools):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid Request"}}
    if "id" not in msg:
        return None  # notification (no execution)
    request_id = msg["id"]
    method = msg.get("method")
    if method == "initialize":
        return {"jsonrpc":"2.0","id":request_id,"result":{
            "protocolVersion":"2025-11-25","capabilities":{"tools":{"listChanged":False}},
            "serverInfo":{"name":"genesis-enterprise-demo","version":"0.1.0"}}}
    if method == "ping":
        return {"jsonrpc":"2.0","id":request_id,"result":{}}
    if method == "tools/list":
        return {"jsonrpc":"2.0","id":request_id,"result":{"tools":tool_catalog()}}
    if method == "tools/call":
        params = msg.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32602,"message":"Invalid params"}}
        try:
            out = tools.call(params["name"], params.get("arguments", {}))
            return {"jsonrpc":"2.0","id":request_id,"result":{"content":[{"type":"text","text":json.dumps(out,sort_keys=True)}],"isError":False}}
        except (ValueError, TypeError, OverflowError) as exc:
            # Only our own fixed validation labels; never echo argument values.
            reason = str(exc) if re.fullmatch(r"[A-Z_]+", str(exc)) else "INPUT_REJECTED"
            return {"jsonrpc":"2.0","id":request_id,"result":{"content":[{"type":"text","text":json.dumps({"state":"BLOCKED","reason":reason})}],"isError":True}}
    return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32601,"message":"Method not found"}}


def main():
    tools = EnterpriseTools(DraftStore(os.environ.get("GENESIS_ENTERPRISE_DRAFT_DB", ":memory:")))
    # Prevent an untrusted peer from forcing unbounded buffers; stdio only.
    while True:
        raw = sys.stdin.buffer.readline(MAX_LINE + 1)
        if not raw:
            break
        if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
            print("Frame size / termination rejected", file=sys.stderr)
            break
        try:
            msg = json.loads(raw)
            resp = dispatch(msg, tools)
        except (UnicodeError, ValueError, json.JSONDecodeError):
            resp = {"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}}
        except Exception:
            # Never spill stack traces or credentials into agent-visible channels.
            resp = {"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"Internal error"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp,separators=(",",":")) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()