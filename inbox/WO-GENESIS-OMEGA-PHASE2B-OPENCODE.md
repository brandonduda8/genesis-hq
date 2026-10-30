# WO-GENESIS-OMEGA-PHASE2B — OpenCode deployment handoff

**Status:** QUEUED_FOR_OPERATOR (this file is not a dispatched or executed task).
**Requested by:** Genesis owner, via ChatGPT: "please just have opencode do it."
**Target host:** `genesis-s1` only after confirming actual host identity.
**Date:** 2026-10-29
**Cost ceiling:** $0 incremental; no paid APIs or new paid infrastructure.
**Priority:** First safe persistent Anchor service; then private Android readiness; then OpenClaw integration assessment.
**Authority:** Genesis canonical approvals and ledger; never invent another controller.

## Source: reported Phase 2A outcome — unverified until inspected on-host

The owner's pasted report claims:
- Production Anchor PID 246478 on `127.0.0.1:8799`, production untouched during tests.
- Isolated Anchor test at `127.0.0.1:8798` with `~/genesis-anchor-test/`.
- Seven reported tests PASS: RAM floor, denied/authorized approvals, STOP completion guard, idempotency, SQLite restart, localhost bind.
- Fixed deadlock in `mission_submit` caused by nested call to `mission_get()` under a non-reentrant lock.
- Modified `genesis-anchor/anchor.py`; prepared `.config/systemd/user/genesis-anchor.service` and `.config/systemd/user/genesis-anchor.env` but did not activate them.
- Receipt is at `genesis-os/war-room/GENESIS-OMEGA-PHASE2A-RECEIPT.md`.
- StarNet blocked pending NetBird reauthentication; no owner token has been shared.

**All of these are claims from a pasted report.** Verify actual file paths, checksums, listener/process identity, running user, state roots and code before any mutation. The historical PID may now be stale.

## Non-negotiable boundaries

1. **No loss of production availability:** never kill, restart, replace, signal, or rebind the service currently serving port 8799 without separate, scoped owner approval and a proven rollback. Never start two Anchor services on the same state directory or bind port.
2. **Private endpoints:** loopback only by default. Do not use `0.0.0.0`, public reverse proxies, port forwarding, router changes, firewall changes, public DNS, or Tailscale Funnel. Tailscale Serve/ACL design may be reviewed, but enabling Android routing requires a separate explicit decision after identity and access testing.
3. **User-level service only:** installation/activation for a **separate, isolated** Anchor sidecar may proceed under the owner's instruction only when a complete preflight demonstrates no production collision and no privileged/system changes. Use `systemctl --user` only. If any unit attempts to own 8799 or existing production state, STOP, do not activate; report precise decision needed.
4. **Secrets stay on-host:** do not open/print env values, credentials, API keys, cookies or private keys into model context, work orders, terminal receipts or Git. Inspect only config key *names* with a non-disclosing tool; redact sensitive command output. Do not authenticate NetBird, Claude, GitHub, or any other service as the owner.
5. **Avoid unsafe assumptions:** inspect original unit, actual Python runtime and paths, current branch/status, repo ownership, mode, dependencies, memory and systemd user manager. Don't fetch, install, migrate, or overwrite unknown data silently.
6. **Spending/external effects:** no money, paid models, account changes, external communications, public deployments, autonomous merges, business outreach, or database writes beyond isolated, scoped test state.
7. **Truthful results:** test claims aren't verified deployment, a socket isn't authenticated service identity, transport ACK isn't mission completion. Preserve `UNKNOWN`, `CLAIMED`, `BLOCKED`, `VERIFIED` distinctions.
8. **No broad permissions:** use OpenCode's existing permission prompts for host-changing shell commands; do not disable tool protections or use unrestricted shells as agents.

## Phase A — read-only reconciliation (mandatory)

- Confirm `hostname`, `id -un`, `pwd`, actual `genesis-os` and `genesis-anchor` source roots (do not guess `~/` layout).
- Read `GENESIS-OMEGA-PHASE2A-RECEIPT.md` and inspect the prepared unit/template by safe allowlisted paths. Never display credential contents.
- Determine source commit/tree state, uncommitted modifications, and whether the deadlock/STOP fixes are in the running build. Check idempotency implementation for multiple concurrent submitters.
- Identify listener at `127.0.0.1:8799` from fresh OS/socket evidence; verify it's actually Anchor and not another process. Also check whether test port 8798 is currently in use.
- Confirm state backing files, backups/rollback and user-unit target; collect only bounded, redacted diagnostics.
- Classify every reported test as `reported`, `reproduced`, `blocked`, or `failed`.

**If the receipt, unit or real source isn't present, do not reconstruct or deploy from memory. Report BLOCKED_SOURCE_NOT_FOUND.**

## Phase B — independently reproduce the isolation tests

- Use a fresh isolated test state with secure permissions and distinct database. Avoid overwriting `~/genesis-anchor-test` or any production state.
- Review test code for side effects before invoking. Test unauthorized/authorized approvals (using test identities only), STOP fence, idempotency under sequential **and concurrent** duplicate requests, SQLite restart, localhost bind, and RAM guard.
- Prove service failed attempt cannot report success; ensure no 8799 process interruption. Verify no idempotency deadlock in timeout-bounded run.
- Record commands (redacted), exit codes, timestamps, exact code revision, any failure, and whether tests used mocks.
- If failures occur, fix on a feature branch or stage a patch; do not force deployment.

## Phase C — safe persistent pilot (strictly conditional)

- Audit user systemd unit for `ExecStart`, `WorkingDirectory`, `EnvironmentFile`, user identity, state directories, restart policy, and termination/rollback behavior; verify the env-file template contains no real secrets.
- Only if all of A/B passed, prepare a **separate** user-owned pilot unit with an isolated state root and an unused loopback-only port. No overlap with the existing 8799 production listener and no shared sqlite DB.
- Installation/activation of this *isolated user-level pilot only* is within the current owner's request when it is provably non-disruptive, reversible, requires no root/system changes, and uses no paid service. If that cannot be proven, leave the unit staged **not enabled** and report the exact required owner tap.
- Start the pilot using `systemctl --user` only when compliant. Verify fresh unit status, localhost response, startup after a controlled pilot-only restart, persistence, stop semantics, and rollback. Do not assume `loginctl enable-linger` authority; request approval separately before changing linger.
- Never automatically cut over, start/stop/restart the existing production Anchor, or claim 24/7 durability based only on unit existence.

## Phase D — private Android and worker integration plan

- **Android:** examine existing Tailscale state, authentication and ACL plan without creating/exposing a listener. Draft a Serve-only (not Funnel) private transport plan and owner decision; do not enable it yet.
- **OpenClaw:** audit currently running version, gateway scope, authentication and reachable localhost contract. Propose one **read-only** heartbeat/capability adapter routed through Genesis canonical policy. No gateway restart and no credential exchange.
- **StarNet:** keep BLOCKED until NetBird reauthentication is completed by the owner and verified. Do not bypass it or silently substitute another transport.
- **Genesis Core:** design an adapter to canonical existing mission/approval/evidence paths. No qualification/financial DB mutation pending review.

## Required final deliverables

1. A non-secret receipt under the existing `genesis-os/war-room/` directory named `GENESIS-OMEGA-PHASE2B-RECEIPT.md` (if the path exists and is writable), with timestamp, source commit, tested ports, state paths (no secrets), test outcomes, systemd state and exact rollback.
2. One machine-readable status summary (if supported) distinguishing `REPORTED`, `OBSERVED`, `VERIFIED`, `BLOCKED`.
3. Minimal reviewable code changes on a branch if needed; no automatic merge, deployment to public endpoints or production cutover.
4. If the isolated user service went live, show independent service-readiness evidence and whether it survives a **pilot-only** restart. If it did not, state exactly why.
5. List next owner decision(s) without asking the owner to repeat information already supplied.

**Acceptance:** no production disruption; independent repeat of critical tests; at most one new isolated, user-level pilot service genuinely confirmed; private Android/OpenClaw follow-up planned; StarNet remains blocked until independently recovered.
