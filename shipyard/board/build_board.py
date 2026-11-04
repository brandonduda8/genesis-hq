#!/usr/bin/env python3
"""Build the Shipyard board data (board.json) from sources.json by asking GitHub, read-only.

Status vocabulary (WO-GENESIS-SHIPYARD-APP-ALIGNMENT-005):
  LIVE    : evidence was fetched just now, it is green, and the newest green item is within fresh_hours
  STALE   : evidence was fetched, but it is old, or the latest CI run on a watched branch is not green
  UNKNOWN : nothing could be fetched (no probes, no network, no access). Never shown as LIVE.

Read-only: only GET requests. Auth comes from GITHUB_TOKEN / GH_TOKEN, or `--via-gh` uses the gh CLI.
Without auth, private repos read as UNKNOWN. That is the honest answer, not an error.

Usage:
  python3 shipyard/board/build_board.py --out shipyard/board/site/board.json [--via-gh] [--now ISO]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
API = "https://api.github.com"
Fetch = Callable[[str], Optional[dict]]


def iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts: Optional[str]) -> Optional[dt.datetime]:
    if not ts:
        return None
    return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def http_fetcher(token: Optional[str]) -> Fetch:
    def fetch(path: str) -> Optional[dict]:
        req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                          "User-Agent": "genesis-shipyard-board"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None
    return fetch


def gh_fetcher() -> Fetch:
    def fetch(path: str) -> Optional[dict]:
        try:
            out = subprocess.run(["gh", "api", path.lstrip("/")], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if out.returncode != 0:
            return None
        try:
            return json.loads(out.stdout)
        except ValueError:
            return None
    return fetch


def probe(p: dict, fetch: Fetch) -> dict:
    """One evidence item. fetched=False means we could not see it (UNKNOWN), never that it failed."""
    base = {"kind": p["kind"], "label": p["label"], "repo": p["repo"], "fetched": False, "ok": False,
            "at": None, "url": None, "sha": None, "detail": "not reachable from this build host"}
    repo = p["repo"]
    if p["kind"] == "ci":
        d = fetch(f"/repos/{repo}/actions/workflows/{p['workflow']}/runs?branch={p['branch']}&per_page=10")
        if d is None:
            return base
        runs = [r for r in d.get("workflow_runs", []) if r.get("status") == "completed"]
        if not runs:
            return {**base, "fetched": True, "detail": "no completed run on this branch"}
        latest = runs[0]
        ok = latest.get("conclusion") == "success"
        return {**base, "fetched": True, "ok": ok, "at": latest.get("updated_at"), "url": latest.get("html_url"),
                "sha": (latest.get("head_sha") or "")[:7],
                "detail": f"latest run {latest.get('conclusion')} on {p['branch']}"}
    if p["kind"] == "branch":
        d = fetch(f"/repos/{repo}/branches/{p['branch']}")
        if d is None:
            return base
        c = d.get("commit", {})
        return {**base, "fetched": True, "ok": True, "at": c.get("commit", {}).get("committer", {}).get("date"),
                "url": c.get("html_url") or f"https://github.com/{repo}/tree/{p['branch']}", "sha": (c.get("sha") or "")[:7],
                "detail": f"{p['branch']}: {c.get('commit', {}).get('message', '').splitlines()[0][:90] if c else ''}"}
    if p["kind"] == "pr":
        d = fetch(f"/repos/{repo}/pulls/{p['number']}")
        if d is None:
            return base
        state = "merged" if d.get("merged") else d.get("state")
        return {**base, "fetched": True, "ok": state in ("open", "merged"), "at": d.get("updated_at"),
                "url": d.get("html_url"), "sha": (d.get("head", {}).get("sha") or "")[:7],
                "detail": f"PR #{p['number']} {state}: {d.get('title', '')[:80]}"}
    return {**base, "detail": f"unknown probe kind {p['kind']}"}


def status(evidence: list[dict], now: dt.datetime, fresh_hours: float) -> tuple[str, str]:
    seen = [e for e in evidence if e["fetched"]]
    if not seen:
        return "UNKNOWN", "no evidence could be fetched" if evidence else "no evidence exists yet"
    failing = [e for e in seen if e["kind"] == "ci" and not e["ok"] and e["at"]]
    if failing:
        return "STALE", f"{failing[0]['label']}: {failing[0]['detail']}"
    green = [parse(e["at"]) for e in seen if e["ok"] and e["at"]]
    if not green:
        return "STALE", "evidence found but none of it is green"
    age_h = (now - max(green)).total_seconds() / 3600
    if age_h > fresh_hours:
        return "STALE", f"newest green evidence is {age_h:.0f} h old (fresh window {fresh_hours:.0f} h)"
    return "LIVE", f"green evidence {age_h:.0f} h old"


def build(sources: dict, fetch: Fetch, now: dt.datetime) -> dict:
    fresh = float(sources.get("fresh_hours", 72))
    apps = []
    for a in sources["apps"]:
        ev = [probe(p, fetch) for p in a.get("probes", [])]
        st, why = status(ev, now, fresh)
        apps.append({k: a[k] for k in ("id", "name", "what", "owner", "qa", "acceptance", "stage_note", "blockers")}
                    | {"status": st, "status_why": why, "evidence": ev})
    return {"schema": "genesis.shipyard.board/1.0", "generated_at": iso(now), "fresh_hours": fresh,
            "law": "LIVE only from fresh, green, fetched evidence. Cached or unfetched is never LIVE.", "apps": apps}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default=str(HERE / "sources.json"))
    ap.add_argument("--out", default=str(HERE / "site" / "board.json"))
    ap.add_argument("--via-gh", action="store_true", help="use the gh CLI's auth instead of GITHUB_TOKEN")
    ap.add_argument("--now", help="override the clock (ISO, for reproducible builds)")
    a = ap.parse_args(argv)
    now = parse(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    fetch = gh_fetcher() if a.via_gh else http_fetcher(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    board = build(json.loads(Path(a.sources).read_text()), fetch, now)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(board, indent=1) + "\n")
    for app in board["apps"]:
        print(f"{app['status']:8} {app['name']}: {app['status_why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
