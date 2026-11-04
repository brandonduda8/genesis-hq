# Genesis Shipyard — Product Delivery Team (v0.1)

**This is not a new autonomous operating system.** It is a small, testable release
queue and approval-gated dispatcher around the **existing** Dragon OS worker
bridge and private `empire-handoffs` bus.

## First product milestones

Read `PRODUCT_QUEUE.json` with `python3 shipyard/shipyard.py queue`.

| Order | Product | What a user must receive | Existing evidence |
|---|---|---|---|
| P1 | Aurum Pulse 2.2 | Android APK + real-phone offline and streaming test + stable signing | genesis-player PR #15 |
| P2 | Omega CSV QA Kit | Offline executable/ZIP + real input/output QA + verified checksum | Agent-x issue #24 |
| P3 | Foundry Lead-to-Quote | Browser app with persistence, quote and export | genesis-hq issue #3 |
| P4 | Genesis Universe | One actual worker canary and verifiable mission receipt in the city | Genesis-core issue #1 |

**Stop starting new products until the first two have actual owner-tested delivery.**

## Engineering team

| Seat | Backing tool | Authority |
|---|---|---|
| Astra — product architect | Genesis planning / code review | Scopes one deliverable and acceptance tests |
| Claude — implementation lead | Existing `team-claude.sh` | Writes **reviewable branches**, no merging |
| Codex — independent engineer | Existing `team-codex.sh` | Reviews/tests or edits an isolated worktree when explicitly authorized |
| Gemini — scout | Existing `team-gemini.sh` | Research and documentation, not release approval |
| OpenHands/OpenCode — optional builders | Existing `openhands-vm`/OpenCode | Use only after real installation, authentication, sandbox audit |
| Themis — security | Audit function | Reviews untrusted MCP/shell and data boundaries |
| Zane — independent QA | Existing audit process | Verifies exact SHA, CI, real device, receipts |
| GHOST — business analyst | Existing revenue lane | Validates customer usefulness and drafts offer; no outreach without approval |

Use one heavy worker at a time. An animated NPC is a *view of a verified worker
state*, never evidence that a job ran.

## Operator procedure

1. In Genesis HQ Codespaces, first confirm GitHub Codespaces has **no paid
   overage allowed**; free allowances and available machine sizes may change.
   Run `bash provision/setup.sh`. Authenticate any chosen CLI on that host.
2. Verify `~/bin/worker-bridge.sh probe`. A CLI showing as installed does not
   prove its credentials or model provider are working. A real minimal task must
   pass before marking a lane READY.
3. Keep actual source repos in isolated worktrees. Set
   `GENESIS_WORKSPACE=/path/to/the/isolated/worktree` when invoking a lane.
   Never point an untrusted model at the production Anchor directory.
4. Draft work orders in the existing **private** empire-handoffs bus. Only
   Zane may record the founder's approval, and the exact byte hash of the order
   must match. Claude must perform the canonical `APPROVED -> CLAIMED`
   transition and claim receipt defined in `PROTOCOL.md`.
5. The Shipyard dispatcher will only run a **CLAIMED** order with valid
   approval marker and claim receipt. Example:
   
   ```bash
   python3 shipyard/shipyard.py queue
   # To check an APPROVED (not claimed yet) order:
   python3 shipyard/shipyard.py verify --bus ~/workspace/empire-handoffs --id WO-SAMPLE-001
   # After canonical CLAIMED transition; this first invocation is dry-run:
   python3 shipyard/shipyard.py dispatch --bus ~/workspace/empire-handoffs --id WO-SAMPLE-001 --lane codex
   # Only after isolated workspace and actual credentials are verified:
   python3 shipyard/shipyard.py dispatch --bus ~/workspace/empire-handoffs --id WO-SAMPLE-001 --lane codex --execute
   ```

   This requires the existing `bin/worker-bridge.sh`; it does not create agents,
   an always-on service, or a scheduler by itself. `WO-SAMPLE-001` is an example
   only; it is not an approved order.
6. The executor writes a local attempt receipt, **not** a delivery certificate.
   The authorized worker follows the existing `CLAIMED -> DONE` handoff
   protocol. Zane verifies the PR, tests, product output and rollback.
   The founder decides merges, publication, money movement and external outreach.

## Security/limits

- $0 incremental expenditure. No auto-subscribing, payment, live trading, or
  unauthorized outreach.
- No GitHub repo merge, production restart, model-secret logging, public
  endpoint binding, or shell access from game NPCs.
- The marker's SHA-256 ties an order to its contents; by itself it is **not
  a cryptographic signature of the founder's identity**. Keep the bus private
  with tightly controlled repo permissions.
- `shipyard.py` does not verify remote agent identity and cannot certify an
  A2A/StarNet network. The Astra–Zane local bridge remains transport-pending
  until a cross-host handshake is independently proven.
- The existing Claude runner allows Bash/Write; that is **not** a sandbox. Run
  it only in a disposable, restricted dev environment until isolation is tested.
- No agents run in the background just because this PR exists. A real host,
  credentials, explicit bus approval, and a scheduled worker service are
  prerequisites for unattended execution.

## Honest release statuses

`BUILT` = code exists; `CI_PASS` = particular test run passed;
`DEVICE_VERIFIED` = tested on actual phone; `QA_ACCEPT` = Zane checked
a reproducible artifact; `OWNER_ACCEPT` = founder used and approved product;
`SHIPPED` = approved delivery accessible to user. No shortcuts.

The code in this feature branch is **candidate tooling** until CI and a
read-only test on a real Genesis HQ host pass. It is not installed on StarNet.

## The Shipyard board (read-only, phone-first)

`shipyard/board/` is the first usable surface of the Shipyard app (WO-GENESIS-SHIPYARD-APP-ALIGNMENT-005, first
engineering checkpoint): one truthful, phone-viewable board of the apps under development.

- `sources.json`: the apps, their owners and blockers (each with a source link), and the evidence **probes**
  (latest CI run on a branch, branch head, PR state). It holds no status claims.
- `build_board.py`: asks GitHub (GET only) and writes `site/board.json`. **LIVE** means fresh, green, fetched evidence;
  **STALE** means old or a non-green latest run; **UNKNOWN** means nothing could be fetched. Unreachable is never LIVE.
- `site/`: a static page (no external scripts, offline-capable, light/dark). If `board.json` is older than its fresh
  window, the page itself downgrades LIVE to STALE and says why.

```bash
python3 -m unittest shipyard/board/test_board.py              # the status law, no network
python3 shipyard/board/build_board.py --via-gh                # or GITHUB_TOKEN=… for private repos
cd shipyard/board/site && python3 -m http.server 8080 --bind 127.0.0.1   # serve privately (loopback / mesh only)
```

Not on the board yet, and labelled as missing rather than faked: approvals, mission intake (needs Anchor/Router
mission IDs), and worker health/stop.
