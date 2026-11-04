"""Tests for the Shipyard board generator: the status law, with a fake GitHub (no network)."""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_board as bb  # noqa: E402

NOW = dt.datetime(2026, 11, 4, 12, 0, tzinfo=dt.timezone.utc)


def at(hours_ago):
    return bb.iso(NOW - dt.timedelta(hours=hours_ago))


def runs(conclusion, hours_ago):
    return {"workflow_runs": [{"status": "completed", "conclusion": conclusion, "updated_at": at(hours_ago),
                               "html_url": "https://github.com/x/y/actions/runs/1", "head_sha": "abcdef123"}]}


def fake(table):
    def fetch(path):
        for k, v in table.items():
            if k in path:
                return v
        return None  # unreachable / private without auth
    return fetch


CI = {"kind": "ci", "label": "battery", "repo": "o/r", "branch": "b", "workflow": "w.yml"}
BR = {"kind": "branch", "label": "head", "repo": "o/r", "branch": "main"}
PR = {"kind": "pr", "label": "pr", "repo": "o/r", "number": 7}


def app(probes):
    return {"id": "a", "name": "A", "what": "w", "owner": "o", "qa": "q", "acceptance": "b", "stage_note": "s",
            "blockers": [], "probes": probes}


class StatusLaw(unittest.TestCase):
    def board(self, probes, table):
        return bb.build({"fresh_hours": 72, "apps": [app(probes)]}, fake(table), NOW)["apps"][0]

    def test_fresh_green_ci_is_live(self):
        a = self.board([CI], {"/actions/workflows/": runs("success", 5)})
        self.assertEqual("LIVE", a["status"])
        self.assertTrue(a["evidence"][0]["ok"])
        self.assertEqual("abcdef1", a["evidence"][0]["sha"])

    def test_old_green_is_stale(self):
        a = self.board([CI], {"/actions/workflows/": runs("success", 100)})
        self.assertEqual("STALE", a["status"])
        self.assertIn("100 h old", a["status_why"])

    def test_failing_latest_run_is_stale_even_if_other_evidence_is_green(self):
        b = {"commit": {"sha": "123456789", "html_url": "u", "commit": {"message": "m", "committer": {"date": at(1)}}}}
        a = self.board([CI, BR], {"/actions/workflows/": runs("failure", 1), "/branches/": b})
        self.assertEqual("STALE", a["status"])
        self.assertIn("failure", a["status_why"])

    def test_unreachable_is_unknown_never_live(self):
        a = self.board([CI, PR], {})
        self.assertEqual("UNKNOWN", a["status"])
        self.assertTrue(all(not e["fetched"] for e in a["evidence"]))

    def test_no_probes_is_unknown_with_honest_reason(self):
        a = self.board([], {})
        self.assertEqual("UNKNOWN", a["status"])
        self.assertEqual("no evidence exists yet", a["status_why"])

    def test_branch_without_any_ci_counts_by_age(self):
        b = {"commit": {"sha": "9", "html_url": "u", "commit": {"message": "x", "committer": {"date": at(200)}}}}
        self.assertEqual("STALE", self.board([BR], {"/branches/": b})["status"])

    def test_closed_unmerged_pr_is_not_green(self):
        a = self.board([PR], {"/pulls/7": {"state": "closed", "merged": False, "updated_at": at(1), "title": "t",
                                            "html_url": "u", "head": {"sha": "1"}}})
        self.assertEqual("STALE", a["status"])

    def test_no_completed_run_is_fetched_but_not_green(self):
        a = self.board([CI], {"/actions/workflows/": {"workflow_runs": [{"status": "in_progress"}]}})
        self.assertEqual("STALE", a["status"])
        self.assertEqual("no completed run on this branch", a["evidence"][0]["detail"])


class SourcesFile(unittest.TestCase):
    def test_shipped_sources_are_well_formed_and_every_blocker_has_a_source(self):
        s = json.loads((Path(__file__).resolve().parent / "sources.json").read_text())
        ids = [a["id"] for a in s["apps"]]
        self.assertEqual(len(ids), len(set(ids)))
        for a in s["apps"]:
            for k in ("name", "what", "owner", "qa", "acceptance", "stage_note", "blockers", "probes"):
                self.assertIn(k, a, f"{a['id']} lacks {k}")
            for b in a["blockers"]:
                self.assertTrue(b["source"].startswith("https://"), b)
            for p in a["probes"]:
                self.assertIn(p["kind"], ("ci", "branch", "pr"))

    def test_offline_build_marks_everything_unknown(self):
        s = json.loads((Path(__file__).resolve().parent / "sources.json").read_text())
        b = bb.build(s, lambda path: None, NOW)
        self.assertTrue(all(a["status"] == "UNKNOWN" for a in b["apps"]))
        self.assertEqual(bb.iso(NOW), b["generated_at"])


if __name__ == "__main__":
    unittest.main()
