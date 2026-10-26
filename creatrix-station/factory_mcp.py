#!/usr/bin/env python3
"""Genesis Cody Factory read-only MCP stdio server (spec 2025-11-25 subset).

Exposes *only* nonsecret local inventory, factory manifest summary, and curated
safety/documentation resources. No shell, HTTP, file edits, key material, or
outside-root reads. Local MCP clients launch this as an unprivileged subprocess.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from cody_factory import available_tools, list_workspaces, integration_plan

PROTOCOL = "2025-11-25"
TOOLS = [
    {"name":"creatrix_toolchain", "description":"Read-only executable presence and placement recommendations; does not launch anything", "inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
    {"name":"creatrix_projects", "description":"Summarize explicitly created factory project manifests; no source/secret file reads", "inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
    {"name":"creatrix_integrations", "description":"Read-only OpenCode, OpenHands, ZeroClaw and SSH pairing requirements", "inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
]


def handle(request:dict,root:Path)->dict|None:
    if not isinstance(request,dict):
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32600,"message":"Invalid JSON-RPC request"}}
    method = request.get("method")
    req_id = request.get("id")
    if not isinstance(method,str):
        return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32600,"message":"Invalid JSON-RPC method"}}
    if method.startswith("notifications/"):
        return None
    if "id" not in request:
        return None
    if method == "initialize":
        return {"jsonrpc":"2.0","id":req_id,"result":{"protocolVersion":PROTOCOL,"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":"genesis-creatrix-factory","version":"2.0.0"}}}
    if method == "ping":
        return {"jsonrpc":"2.0","id":req_id,"result":{}}
    if method == "tools/list":
        return {"jsonrpc":"2.0","id":req_id,"result":{"tools":TOOLS}}
    if method == "tools/call":
        p=request.get("params",{})
        if not isinstance(p,dict):
            return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32602,"message":"Invalid params"}}
        name=p.get("name")
        args=p.get("arguments",{})
        if args not in ({},None) or name not in {t["name"] for t in TOOLS}:
            return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32602,"message":"Unsupported tool or arguments"}}
        if name=="creatrix_toolchain":data={"tools":available_tools(),"attestation":"EXECUTABLE_PRESENCE_ONLY"}
        elif name=="creatrix_projects":data={"projects":list_workspaces(root),"attestation":"LOCAL_MANIFESTS_ONLY"}
        else:data=integration_plan()
        result={"content":[{"type":"text","text":json.dumps(data,separators=(",",":"))}],"isError":False}
        return {"jsonrpc":"2.0","id":req_id,"result":result}
    return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Method not found"}}


def run(stdin=None,stdout=None,data_dir:Path|None=None)->int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    data_dir = data_dir or Path.home()/".local"/"share"/"genesis-creatrix"
    for line in stdin:
        if len(line)>65536:
            # No id can be safely recovered from oversize data.
            continue
        try:
            request=json.loads(line)
            result=handle(request,data_dir)
        except (ValueError,TypeError,KeyError):
            result={"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}}
        if result is not None:
            stdout.write(json.dumps(result,separators=(",",":"))+"\n")
            stdout.flush()
    return 0


if __name__=="__main__":
    raise SystemExit(run())
