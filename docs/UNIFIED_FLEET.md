# Genesis unified fleet — Phase 1 observer

**Scope:** add one read-only observation command to the existing Genesis HQ worker bridge. This is **not** a second brain, scheduler, permission engine, worker registry, or live connectivity claim.

## Use

From a Genesis HQ checkout:

```sh
bash bin/worker-bridge.sh fleet
bash bin/worker-bridge.sh fleet --json
python3 -m unittest discover -s tests -p 'test_fleet_status.py' -v
```

After the existing HQ provisioner copies the `.sh` scripts into `~/bin`:

```sh
~/bin/worker-bridge.sh fleet --json
```

The observer performs **only** `command -v` lookups and `-f` marker checks. It does **not** execute a worker, read credentials, attempt network requests, read arbitrary source content, install packages, or start a server.

Optional custom checkout roots (not credentials):

- `GENESIS_AGENT_X_ROOT` defaults to `$HOME/workspace/Agent-x`
- `GENESIS_CORE_ROOT` defaults to `$HOME/workspace/genesis_core`
- `GENESIS_MAILBOX_ROOT` defaults to `$HOME/genesis-openclaw-mailbox`

## Evidence semantics

| State | Meaning |
| --- | --- |
| `CLI_PRESENT_UNVERIFIED` | CLI name resolves on this host; *no* proof of login, API entitlement, working model, or a successful task |
| `SOURCE_PRESENT_UNVERIFIED` | A recognized local source marker exists; *no* proof of build, service, or tests |
| `ADAPTER_CODE_ONLY` | StarNet integration code is present, but no transport or worker run is proven |
| `NOT_OBSERVED` | This limited check did not see it. Not a claim it is absent elsewhere |
| `UNMAPPED` | Alias exists in the owner's requested fleet but the exact implementation/interface has not been located |

The observer includes installed-CLI checks for Claude, Codex, Gemini, OpenCode, Goose, Aider, Hermes, OpenHands, Ruflo, Agent Zero, Cody, and OpenClaw; source markers for Agent X, Genesis Core, and the OpenClaw mailbox; an adapter-only StarNet marker; and explicit unmapped statuses for ACE, Ghost, and Prime. It is a **view**, not another canonical capabilities database.

## Canonical responsibilities

1. **Genesis Core** remains the single mission, authorization, policy, scheduling, ledger, and verification authority.
2. **Phoenix** renders live or stale evidence with truthful statuses; it does not promote observation into VERIFIED.
3. **Agent X / Cody** remains a bounded coding and resource worker. Reuse its existing `cody doctor`, admission control, OpenClaw mailbox, StarNet envelope and ledger code.
4. **Genesis HQ** remains a CLI/worker bridge and read-only fleet observer. Its existing `run` path is unchanged.
5. **Claude, Codex, Gemini, OpenCode, Goose, Aider, Hermes, OpenHands, Ruflo, Agent Zero** require individually audited, host-specific, user-authorized adapter and runtime tests before dispatch.
6. **StarNet** remains adapter-only until the upstream transport is independently confirmed. **ACE, Ghost, Prime** remain unmapped until their actual source/interface is identified.

## Next engineering gates (not yet performed)

- Reconcile actual local canonical Genesis paths, worker fabric, ApprovalGateway and resource/model registries. Do not overwrite them with HQ metadata.
- Obtain a **non-sensitive** snapshot from each authorized machine with `fleet --json`; attest host, timestamp and commit separately in Genesis rather than trusting a worker claim.
- For one worker at a time, validate exact CLI/SDK version, official API contract, authentication **without reading secrets**, sandbox, budget, allowed actions, tests and failure behavior.
- Use existing versioned work-order + mailbox protocols to deliver bounded jobs. No direct arbitrary shell transport, impersonation, silent model fallback, automated payments/outreach, autonomous deployment or publishing.
- Require owner approval for consequential actions and keep $0 spend default. Only independently verified receipts can mark tasks complete.
- Continue with a draft PR per adapter, test each one, then feed actual reports to Phoenix through existing Genesis APIs/events.

**Current milestone:** a locally tested observer and a proposed bridge entry point. **Not** a live multi-agent deployment. Codex/Claude subscriptions and CLI sign-in must be independently verified; installing a CLI does not grant paid provider access.
