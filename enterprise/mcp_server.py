#!/usr/bin/env python3
"""Genesis Enterprise MCP v0.1: local stdio-only, demo/draft-only.
No provider API, actual money, outreach, remote compute or credentials.
NOT a production financial controller or tenant-isolated service.
"""
import json
import sqlite3
import sys
import hashlib
import re
from datetime import datetime, timezone

MAX_FRAME = 65536
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")

def deny(reason):
    return {"status":"BLOCKED","reason":reason}

def text(x, name, size=240):
    if not isinstance(x, str) or not x.strip() or len(x)>size or any(ord(c)<32 for c in x):
        raise ValueError("INVALID_" + name.upper())
    return x.strip()

def cents(x):
    if isinstance(x, bool) or not isinstance(x, int) or x < 1 or x > 100000000:
        raise ValueError("INVALID_AMOUNT")
    return x

def assert_keys(a, required):
    if not isinstance(a, dict) or set(a) != set(required):
        raise ValueError("INVALID_ARGUMENTS")

class Drafts:
    """Not an accounting ledger: stores unsigned/unissued drafts only."""
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None)
        self.db.execute("CREATE TABLE drafts(ref TEXT PRIMARY KEY, kind TEXT, idem TEXT UNIQUE, fingerprint TEXT, content TEXT, created TEXT)")

    def put(self, kind, idem, data):
        idem=text(idem,"idempotency",80)
        if not SAFE_ID.fullmatch(idem): raise ValueError("BAD_IDEMPOTENCY")
        payload=json.dumps(data,sort_keys=True,separators=(",",":"))
        fp=hashlib.sha256((kind+"\0"+payload).encode()).hexdigest()
        ref="draft-"+hashlib.sha256((kind+"\0"+idem).encode()).hexdigest()[:24]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.db.execute("SELECT ref,kind,fingerprint FROM drafts WHERE idem=?",(idem,)).fetchone()
            if row:
                if (row[1],row[2]) != (kind,fp): raise ValueError("IDEMPOTENCY_CONFLICT")
                result={"ref":row[0],"state":"DRAFT_PENDING_OWNER_REVIEW","duplicate":True}
            else:
                self.db.execute("INSERT INTO drafts VALUES (?,?,?,?,?,?)",(ref,kind,idem,fp,payload,datetime.now(timezone.utc).isoformat()))
                result={"ref":ref,"state":"DRAFT_PENDING_OWNER_REVIEW","duplicate":False}
            self.db.execute("COMMIT")
            return result
        except Exception:
            self.db.execute("ROLLBACK")
            raise

TOOLS={
    "system.status":{"description":"Truthful local-only demo readiness.","properties":{},"required":[]},
    "contracts.qualify":{"description":"Score caller-supplied UNVERIFIED opportunity; never visits website.","properties":{"title":{"type":"string"},"source_url":{"type":"string"},"budget_cents":{"type":"integer"},"fit_percent":{"type":"integer"}},"required":["title","source_url","budget_cents","fit_percent"]},
    "contracts.draft_proposal":{"description":"Draft only; never sends or signs proposals.","properties":{"title":{"type":"string"},"scope":{"type":"string"},"price_cents":{"type":"integer"}},"required":["title","scope","price_cents"]},
    "compute.plan":{"description":"No GPU admission without host attestations; no execution.","properties":{"workload":{"type":"string"},"estimated_ram_mib":{"type":"integer"},"requires_gpu":{"type":"boolean"}},"required":["workload","estimated_ram_mib","requires_gpu"]},
    "pay.invoice_draft":{"description":"Create unsigned, unissued invoice in temporary local demo memory.","properties":{"client_alias":{"type":"string"},"purpose":{"type":"string"},"amount_cents":{"type":"integer"},"currency":{"type":"string","enum":["USD"]},"idempotency_key":{"type":"string"}},"required":["client_alias","purpose","amount_cents","currency","idempotency_key"]},
    "pay.spend_request":{"description":"Plan a purchase request only. No agent can approve or move funds.","properties":{"agent_id":{"type":"string"},"merchant_alias":{"type":"string"},"purpose":{"type":"string"},"amount_cents":{"type":"integer"},"currency":{"type":"string","enum":["USD"]},"idempotency_key":{"type":"string"}},"required":["agent_id","merchant_alias","purpose","amount_cents","currency","idempotency_key"]}
}

def call(name, args, drafts):
    if name not in TOOLS: raise ValueError("UNKNOWN_TOOL")
    assert_keys(args,TOOLS[name]["required"])
    if name=="system.status":
        return {"status":"LOCAL_DEMO_ONLY","live_payments":False,"outreach_enabled":False,"cloud_dispatch_enabled":False,
                "canonical_genesis_ledger_connected":False,"real_income_verified_cents":0}
    if name=="contracts.qualify":
        t=text(args["title"],"title")
        url=text(args["source_url"],"source_url",500)
        if not url.startswith("https://") or any(x in url for x in ('@','#',' ')): raise ValueError("INVALID_SOURCE")
        b=cents(args["budget_cents"])
        fit=args["fit_percent"]
        if isinstance(fit,bool) or not isinstance(fit,int) or fit<0 or fit>100: raise ValueError("INVALID_FIT")
        return {"status":"UNVERIFIED_CANDIDATE","title":t,"source":url,"budget_cents":b,
                "fit_score":fit,"eligible":None,"listing_verified":False,"action":"review_listing_before_proposal"}
    if name=="contracts.draft_proposal":
        return {"status":"DRAFT_NOT_SENT","title":text(args["title"],"title"),
                "scope":text(args["scope"],"scope",500),"price_cents":cents(args["price_cents"]),
                "currency":"USD","send_authorized":False}
    if name=="compute.plan":
        memory=args["estimated_ram_mib"]
        if isinstance(memory,bool) or not isinstance(memory,int) or memory<1 or memory>1000000: raise ValueError("INVALID_RAM")
        if not isinstance(args["requires_gpu"],bool): raise ValueError("INVALID_GPU_FLAG")
        return {"status":"UNVERIFIED_COMPUTE_PLAN","workload":text(args["workload"],"workload"),
                "estimated_ram_mib":memory,"requires_gpu":args["requires_gpu"],
                "worker":None,"actual_gpu_allocated":False,"additional_spend_usd":0}
    if name in ("pay.invoice_draft","pay.spend_request"):
        if args["currency"]!="USD": raise ValueError("UNSUPPORTED_CURRENCY")
        raw={"purpose":text(args["purpose"],"purpose",500),
             "amount_cents":cents(args["amount_cents"]),"currency":"USD"}
        if name=="pay.invoice_draft":
            raw["client_alias"]=text(args["client_alias"],"client_alias")
            kind="invoice"
        else:
            raw["agent_id"]=text(args["agent_id"],"agent_id",80)
            raw["merchant_alias"]=text(args["merchant_alias"],"merchant_alias")
            kind="spend_request"
        saved=drafts.put(kind,args["idempotency_key"],raw)
        return {**saved,"verified_payment":False,"money_moved":False,
                "authorized_spend_cents":0,"provider_receipt":None}
    raise ValueError("UNKNOWN_TOOL")

def rpc(msg,drafts):
    if not isinstance(msg,dict) or msg.get("jsonrpc")!="2.0":
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid Request"}}
    if "id" not in msg: return None
    mid=msg["id"]
    method=msg.get("method")
    if method=="initialize":
        return {"jsonrpc":"2.0","id":mid,"result":{"protocolVersion":"2025-11-25","capabilities":{"tools":{"listChanged":False}},
                "serverInfo":{"name":"genesis-enterprise-mcp-demo","version":"0.1.0"}}}
    if method=="ping": return {"jsonrpc":"2.0","id":mid,"result":{}}
    if method=="tools/list":
        return {"jsonrpc":"2.0","id":mid,"result":{"tools":[{"name":k,"description":v["description"],
                "inputSchema":{"type":"object","properties":v["properties"],"required":v["required"],
                "additionalProperties":False}} for k,v in TOOLS.items()]}}
    if method=="tools/call":
        p=msg.get("params")
        if not isinstance(p,dict) or not isinstance(p.get("name"),str):
            return {"jsonrpc":"2.0","id":mid,"error":{"code":-32602,"message":"Invalid params"}}
        try:
            out=call(p["name"],p.get("arguments",{}),drafts)
            return {"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":json.dumps(out,sort_keys=True)}],"isError":False}}
        except (ValueError,TypeError) as e:
            reason=str(e) if re.fullmatch(r"[A-Z_]+",str(e)) else "INPUT_REJECTED"
            return {"jsonrpc":"2.0","id":mid,"result":{"content":[{"type":"text","text":json.dumps(deny(reason))}],"isError":True}}
    return {"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":"Method not found"}}

def main():
    drafts=Drafts()
    while True:
        data=sys.stdin.buffer.readline(MAX_FRAME+1)
        if not data: return
        if len(data)>MAX_FRAME or not data.endswith(b"\n"):
            print("Invalid frame size",file=sys.stderr)
            return
        try:
            response=rpc(json.loads(data),drafts)
        except (ValueError,UnicodeError,TypeError):
            response={"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}}
        except Exception:
            response={"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"Internal error"}}
        if response is not None:
            sys.stdout.write(json.dumps(response,separators=(",",":"))+"\n")
            sys.stdout.flush()

if __name__=="__main__":
    main()
