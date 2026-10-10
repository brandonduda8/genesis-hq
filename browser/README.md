# Genesis Browser Lab v0.1 — governed web automation

**A runnable prototype using an installed Chromium browser and Playwright.** Designed as the browser-execution/evidence arm of the Genesis operating system, not a standalone replacement for Firefox/Chrome or a credential-holding always-on AI agent.

## What works *today*

- Functional phone-friendly local browser lab at `http://127.0.0.1:8789`: one tap runs an **owned synthetic** form workflow, displays per-action results, a screenshot from real Chromium, plan digest and review status.
- Strict JSON plans with semantic Playwright roles; an inert preflight by default; external HTTPS **observation-only** (navigation/text/assertions/screenshot/snapshot) behind exact origin allowlists. The isolated test environment blocks outbound browser navigation, so no real external-site run was certified.
- Fixture-only `fill`, `click` and `select` require precise action IDs authorized in a local approval file tied to the plan SHA-256. The local lab's explicit Run button authorizes only the bundled synthetic action IDs. This is **not** a cryptographically authenticated Genesis owner approval service.
- Every attempted step gets a bounded outcome; a failing assertion stops the run without quiet success. Screenshot/text artifacts are hashed; receipt JSON includes plan digest and remains `EXECUTED_NOT_INDEPENDENTLY_VERIFIED` until a separate real reviewer signs off.
- No model invocation, auto-installs, credential stores, billing, outreach, external-site writes, arbitrary JavaScript snippets, unrestricted shell, account actions, public scheduler, or 24/7 worker.
- Network interception uses exact origin and method restrictions; service workers and popups are blocked. These are **not** OS/network sandbox guarantees, and DNS rebind/HTTP navigation side effects require a hardened container and real authorization before trusted deployment.

## Try the current build (for an engineering operator)

Requirements: Python 3.11+, installed `playwright` Python package and installed Chromium. The tested development environment had Python 3.13.5, Playwright 1.57.0, and system Chromium. No packages are installed automatically.

```sh
python3 -m genesis_browser.lab --port 8789
```

Open `http://127.0.0.1:8789` **on that machine** and press **Run approved fixture**. The tab displays the evidence. No phone exposure is assumed (that requires a separate authenticated gateway and approval).

To validate a JSON plan without launching a browser:

```sh
python3 -m genesis_browser.cli examples/fixture_plan.json --fixture
```

To run the fixture via CLI, use the local UI above for the approved action flow. For real external targets, browser access is observation-only; no browser navigation to third-party websites was tested in this build and no account credentials are authorized. There is no automatic agent-driven plan generation yet.

## Tests

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py' -v
```

All 27 tests passed on 2026-10-09, including real Chromium `set_content` fixture interaction and authenticated-local-origin API behavior. The execution environment disallowed HTTP navigation to its own loopback browser test server (`ERR_BLOCKED_BY_ADMINISTRATOR`); therefore the fixture is rendered directly into real Chromium DOM using `page.set_content`, with no network request. Screenshots prove the UI renderer and interactions, **not** a live website navigation or external application automation. Runtime details: `evidence/TEST_REPORT.md`.

## Security and ownership

- Treat all page content as **untrusted data**, not instructions. v0.1 uses deterministic steps with no LLM ingestion.
- Do not place real account credentials or customer data into plans, lab forms, traces or screenshots. Evidence can contain DOM text and is deliberately private, local and unredacted; do not commit real-world run artifacts to GitHub.
- Read-only browsing is a best-effort browser-action constraint; even HTTP GETs can mutate some poorly designed sites. Never claim it proves safe production behavior.
- BrowserContext isolation provides clean browser state, not a host security boundary. Run real domains only inside a network-restricted isolated worker, with owner-authorized domains and credential scopes. No public website automation is enabled by this prototype.
- Origin filter is hostname-based and does not resolve DNS or guarantee protection from DNS-rebinding/IP pivoting. Production needs OS sandbox/egress policy and DNS/IP controls.
- Playwright's upstream Apache-2.0 license and NOTICE apply to upstream components. We do not vendor its binaries/source. Attribution: https://github.com/microsoft/playwright . Existing source dossier pins v1.64.0, but **this run tested v1.57.0**; it must be requalified before production.

## Product blueprint / alliance integration

1. **v0.1: Observe + synthetic approved action (implemented).** Deterministic mission plan, receipts, local UI. Evidence-first limits are explicit.
2. **v0.2: A2A and MissionOS adapter (not implemented).** Genesis canonical dispatcher issues scoped immutable browser jobs. Ruflo routes dependencies; workers execute browser plans; receipts go back to an authenticated Phoenix evidence feed. Validate SHA-256 chain, lease epochs, per-agent ACK and separate verifier; no second permission authority.
3. **v0.3: Authorized real-world business workflow (not implemented).** Choose one owner-owned staging website, establish strong host/network isolation and explicit site/domain/action allowlists, then demonstrate repeated lead-intake-to-quote automation. Include pause/abort, reconciliation after crash, anti-prompt-injection testing, WebSocket blocking, storage lifecycle, and resource limits.
4. **v1: Creator-facing product (proposed).** A browser mission composer, agent/team handoffs, verified checkouts and skill recipes, multi-browser compatibility, signed artifacts and replayable fixtures. Offer portability, not black-box paywall.

## Existing research and alternatives

- Genesis RE department's pinned Playwright behavior dossier: `shared/reverse-engineering/research/20261008T134423Z-playwright-behavior-dossier-v1.md` in `brandonduda8/astra-zane-bridge`.
- Official Playwright MCP: https://github.com/microsoft/playwright-mcp — semantic, accessibility-tree-based agent tools; preferred interoperable adapter candidate over writing our own ad hoc screen driver.
- Browser Use: https://github.com/browser-use/browser-use — useful OSS agent-harness ideas, but requires explicit model/cost/permission qualification.
- Existing Gemini Antigravity/OpenHands/A2A/Ruflo resources: candidate consumers, not assumed connected or running.

## Review checklist

- Run all tests from clean checkout and reproduce one local fixture receipt/screenshots.
- Threat-model network escape, credential scopes, injected page content, per-action approval, trace privacy, tamper-proof receipts, crashes, popup/websocket and timeout behavior.
- Fix known limitations and implement actual owner identity / canonical permission authority before exposing any sensitive browser action.
- Confirm upstream Playwright/browser version pin and MIT/Apache notices for any new dependencies. No billing, accounts, installs, scheduler changes, merges, public exposure or outreach until explicitly approved.
