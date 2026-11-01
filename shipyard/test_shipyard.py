"""Offline tests for the Genesis Shipyard approval boundary. No model keys needed."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shipyard


class ShipyardGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "empire-handoffs"
        self.folder = self.root / "queue" / "approved"
        self.folder.mkdir(parents=True)
        (self.root / "PROTOCOL.md").write_text("# bus")
        self.order_id = "WO-SHIPYARD-TEST-001"
        self.order = self.folder / (self.order_id + ".md")
        self.order.write_text("BUILD: unit-test-only\n")
        self.marker = self.folder / (self.order_id + ".APPROVED")
        self.approve()

    def approve(self):
        self.marker.write_text(json.dumps({
            "id": self.order_id, "approved_by": "Brandon",
            "recorded_by": "Zane", "approved_at": "2026-11-01T19:00:00Z",
            "wo_sha256": hashlib.sha256(self.order.read_bytes()).hexdigest()
        }))

    def claim(self):
        claimed = self.root / "queue" / "claimed"
        claimed.mkdir()
        self.order = self.order.rename(claimed / self.order.name)
        self.marker = self.marker.rename(claimed / self.marker.name)
        digest = hashlib.sha256(self.order.read_bytes()).hexdigest()
        (claimed / (self.order_id + ".CLAIM.json")).write_text(json.dumps({
            "id": self.order_id,
            "claimed_by": "claude",
            "approval_sha256": digest
        }))

    def test_approved_but_unclaimed_order_cannot_dispatch(self):
        with self.assertRaises(shipyard.GateError):
            shipyard.dispatch(self.root, self.order_id, "codex", execute=True)

    def test_corrupted_claim_blocked(self):
        self.claim()
        p = self.order.parent / (self.order_id + ".CLAIM.json")
        obj = json.loads(p.read_text())
        obj["approval_sha256"] = "0" * 64
        p.write_text(json.dumps(obj))
        with self.assertRaises(shipyard.GateError):
            shipyard.dispatch(self.root, self.order_id, "codex", execute=True)

    def test_valid_approval(self):
        self.assertEqual(shipyard.approved_order(self.root, self.order_id)[0], self.order)

    def test_missing_approval_blocked(self):
        self.marker.unlink()
        with self.assertRaises(shipyard.GateError):
            shipyard.approved_order(self.root, self.order_id)

    def test_modified_work_order_blocked(self):
        self.order.write_text("ALTERED AFTER APPROVAL")
        with self.assertRaises(shipyard.GateError):
            shipyard.approved_order(self.root, self.order_id)

    def test_owner_cannot_be_faked_in_marker(self):
        data = json.loads(self.marker.read_text())
        data["approved_by"] = "autonomous-agent"
        self.marker.write_text(json.dumps(data))
        with self.assertRaises(shipyard.GateError):
            shipyard.approved_order(self.root, self.order_id)

    def test_invalid_order_id_blocked(self):
        with self.assertRaises(shipyard.GateError):
            shipyard.approved_order(self.root, "../../etc/shadow")

    def test_dry_run_never_launches_runner(self):
        self.claim()
        with patch.object(shipyard.subprocess, "run") as run:
            self.assertEqual(shipyard.dispatch(self.root, self.order_id, "codex"), 0)
            run.assert_not_called()

    def test_unknown_lane_blocked(self):
        with self.assertRaises(shipyard.GateError):
            shipyard.dispatch(self.root, self.order_id, "shell", execute=True)

    def test_valid_order_exits_and_writes_receipt(self):
        self.claim()
        bridge = self.root / "worker-bridge.sh"
        bridge.write_text("#!/usr/bin/env bash\nexit 0\n")
        receipt_dir = self.root / "receipts"
        with patch.object(shipyard.subprocess, "run", return_value=type("R", (), {"returncode": 0})()) as run:
            self.assertEqual(shipyard.dispatch(self.root, self.order_id, "codex",
                                                execute=True, bridge=bridge,
                                                receipt_dir=receipt_dir), 0)
            self.assertEqual(run.call_count, 1)
            record = json.loads(next(receipt_dir.glob("*.json")).read_text())
            self.assertEqual(record["result"], "WORKER_EXIT_ZERO")
            self.assertIn("not proof", record["qualification"])

    def test_repeat_dispatch_blocked(self):
        self.claim()
        bridge = self.root / "worker-bridge.sh"
        bridge.write_text("#!/usr/bin/env bash\nexit 0\n")
        d = self.root / "receipts"
        with patch.object(shipyard.subprocess, "run", return_value=type("R", (), {"returncode": 0})()):
            shipyard.dispatch(self.root, self.order_id, "codex", True, bridge, d)
            with self.assertRaises(shipyard.GateError):
                shipyard.dispatch(self.root, self.order_id, "codex", True, bridge, d)

    def test_queue_priorities_are_unique(self):
        entries = shipyard.products()
        self.assertEqual([x["priority"] for x in entries], [1, 2, 3, 4])
        self.assertEqual(len({x["id"] for x in entries}), len(entries))


if __name__ == "__main__":
    unittest.main()
