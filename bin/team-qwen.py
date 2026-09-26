#!/usr/bin/env python3
"""team-qwen.py — run one bounded Qwen work order via the local Groq proxy.

Usage: team-qwen.py <work-order-file>

Work-order file: plain prompt text. If the first line is "OUTBOX: <path>",
the final message is saved there (and the line stripped from the prompt).

Qwen (qwen3.8-27b on Groq's free tier) is the alternate-reasoning lane:
strong tool-style instruction following, separate quota from Gemini.
Keep prompts small — Groq on_demand = 8000 TPM and the first request of a
session is token-heavy.

Model override: QWEN_MODEL (default qwen/qwen3.8-27b).
One mission at a time (one-heavy-worker policy).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

PROXY = "http://127.0.0.1:18794/v1/chat/completions"
MODEL = os.environ.get("QWEN_MODEL", "qwen/qwen3.8-27b")
UA = "groq-skill/1.0 (compatible)"  # Cloudflare 1010 bans bare Python UAs


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: team-qwen.py <work-order-file>", file=sys.stderr)
        return 2
    wo = sys.argv[1]
    if not os.path.isfile(wo):
        print(f"no such work order: {wo}", file=sys.stderr)
        return 2
    with open(wo, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    outbox = ""
    if lines and lines[0].startswith("OUTBOX:"):
        outbox = lines[0].split(":", 1)[1].strip()
        prompt = "\n".join(lines[1:])
    else:
        prompt = "\n".join(lines)

    system = (
        "You are Qwen, a bounded worker on Brandon's engineering team. "
        "Your operator is Muse (Zane). Do ONLY what the work order says. "
        "Keep your answer short and factual. Never commit, push, restart "
        "services, or reach the network beyond localhost. If anything is "
        "ambiguous, report it instead of guessing."
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"WORK ORDER:\n{prompt}"},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode()
    req = urllib.request.Request(
        PROXY, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer proxy",
                 "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001
        print(f"qwen run failed: {exc}", file=sys.stderr)
        return 1
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"qwen run failed: unexpected response {str(data)[:200]}",
              file=sys.stderr)
        return 1
    if outbox:
        with open(outbox, "w", encoding="utf-8") as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
