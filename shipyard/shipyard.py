#!/usr/bin/env python3
"""Genesis Shipyard: approved-only worker handoff, with zero implied production authority.

No scheduler, GitHub write, payments, or secrets. Uses existing Genesis HQ worker bridge.
A hash-matched APPROVED marker is required before any agent is invoked.
"""
import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ORDER_RE = re.compile(r"^WO-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
LANES = ("codex", "claude", "gemini")
BASE = Path(__file__).resolve().parent
QUEUE = BASE / "PRODUCT_QUEUE.json"
BRIDGE = BASE.parent / "bin" / "worker-bridge.sh"


class GateError(ValueError):
    pass


def approved_order(bus: Path, order_id: str):
    """Validate the existing empire-handoffs bus approval, not a GitHub issue label."""
    if not ORDER_RE.fullmatch(order_id):
        raise GateError("Invalid work-order ID")
    root = bus.resolve(strict=True)
    protocol = root / "PROTOCOL.md"
    if not protocol.is_file():
        raise GateError("Not an empire-handoffs checkout (PROTOCOL.md missing)")
    folder = root / "queue" / "approved"
    order = folder / (order_id + ".md")
    approval = folder / (order_id + ".APPROVED")
    if not order.is_file() or not approval.is_file():
        raise GateError("Order is not in the approved bus queue")
    contents = order.read_bytes()
    try:
        marker = json.loads(approval.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise GateError("Approval marker is unreadable")
    digest = hashlib.sha256(contents).hexdigest()
    if not isinstance(marker, dict) or (
        marker.get("id") != order_id
        or marker.get("approved_by") != "Brandon"
        or marker.get("recorded_by") != "Zane"
        or marker.get("wo_sha256") != digest
    ):
        raise GateError("Approval marker missing/invalid or work order changed")
    return order, digest


def products():
    raw = json.loads(QUEUE.read_text(encoding="utf-8"))
    return sorted(raw["products"], key=lambda p: p["priority"])


def report_queue(as_json=False):
    entries = products()
    if as_json:
        print(json.dumps(entries, indent=2))
    else:
        for p in entries:
            print(f"P{p['priority']}  {p['name']} — {p['next_gate']}")
            print(f"  {p['evidence_url']}")
    return 0


def dispatch(bus: Path, order_id: str, lane: str, execute=False,
             bridge: Path = BRIDGE, receipt_dir: Path | None = None):
    if lane not in LANES:
        raise GateError("Unknown worker lane")
    order, digest = approved_order(bus, order_id)
    if not execute:
        print(f"VALID APPROVAL: {order_id}; lane={lane}; sha256={digest}")
        print("DRY RUN ONLY: pass --execute to invoke the existing worker bridge.")
        return 0
    if not bridge.is_file():
        raise GateError(f"Worker bridge not found: {bridge}")
    result_dir = (receipt_dir or (bus / "shipyard-receipts")).resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = result_dir / (order_id + "-" + digest[:16] + "-" + lane + ".json")
    # Lock before starting work: concurrent callers must never launch the same
    # order twice. A STARTED receipt survives a crash and blocks silent replay.
    with (result_dir / ".dispatch.lock").open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if receipt_file.exists():
            raise GateError("This order has already been dispatched (receipt exists)")
        receipt = {
            "schema": "genesis.shipyard.dispatch/1.0",
            "order_id": order_id, "order_sha256": digest, "lane": lane,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "result": "STARTED_NOT_VERIFIED",
            "exit_code": None,
            "qualification": "Exit code is not proof of tested code, reviewed PR, or a shipped product."
        }
        with receipt_file.open("x", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        # No shell=True; do not capture or print model output/credentials in receipt.
        try:
            result = subprocess.run(["bash", str(bridge), "run", lane, str(order)],
                                    check=False)
            code = result.returncode
        except OSError:
            code = 127
        receipt.update(
            result="WORKER_EXIT_ZERO" if code == 0 else "WORKER_FAILED",
            exit_code=code,
            finished_at_utc=datetime.now(timezone.utc).isoformat()
        )
        # The STARTED receipt existed before the worker ran; no duplicate launch.
        receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Dispatch receipt: {receipt_file} (exit={code})")
    return code

def main(argv=None):
    ap = argparse.ArgumentParser(description="Genesis Shipyard — evidence-first developer team")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue", help="Show product release priorities")
    q.add_argument("--json", action="store_true")
    v = sub.add_parser("verify", help="Verify bus approval without starting an agent")
    v.add_argument("--bus", type=Path, required=True)
    v.add_argument("--id", required=True)
    d = sub.add_parser("dispatch", help="Run one approved work order using existing HQ bridge")
    d.add_argument("--bus", type=Path, required=True)
    d.add_argument("--id", required=True)
    d.add_argument("--lane", choices=LANES, required=True)
    d.add_argument("--execute", action="store_true", help="Actually start the approved worker")
    d.add_argument("--bridge", type=Path, default=BRIDGE)
    d.add_argument("--receipt-dir", type=Path)
    ns = ap.parse_args(argv)
    try:
        if ns.cmd == "queue":
            return report_queue(ns.json)
        if ns.cmd == "verify":
            _, digest = approved_order(ns.bus, ns.id)
            print(f"APPROVAL VALID: {ns.id} sha256={digest}")
            return 0
        if ns.cmd == "dispatch":
            return dispatch(ns.bus, ns.id, ns.lane, ns.execute, ns.bridge, ns.receipt_dir)
    except (GateError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
