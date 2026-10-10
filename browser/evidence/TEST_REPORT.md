# Genesis Browser v0.1 test evidence — 2026-10-09

## Real current test results

- Ran `PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py' -v` from source checkout: **27 passing / 0 failures / 0 skipped**.
- Python: 3.13.5; `playwright` installed: 1.57.0; Chromium: system `/usr/bin/chromium`.
- Scope: policy rejection/allowlists, duplicate fields/action IDs, bounded run options, per-action digest-tied local fixture approval, read-only preflight; real Chromium DOM rendering of bundled synthetic fixture with semantic actions, screenshot and text artifact receipts; false assertion yields failure and stops before screenshot; local web API origin protection, project validation and evidence retrieval.
- Rendered responsive dashboard in Chromium at desktop 1330x960 and mobile 390x860: **no horizontal scroll**. Screenshots saved as `desktop_console.png`, `mobile_console.png`.
- Development browser **cannot navigate via HTTP to its own loopback fixture** due administrator network policy (`net::ERR_BLOCKED_BY_ADMINISTRATOR`), despite Python's local HTTP server working. Adapted the synthetic fixture runner to `page.set_content` (real Chromium DOM, no HTTP). The synthetic demo therefore **does not prove browser networking or external-site control**.
- No real sites, customer data, logins, payments, public service, external model calls or third-party API activity.
- Security limitations: exact-hostname interception is not a complete network sandbox; external observation only, not proven safe against DNS rebinding. No independent reviewer yet; receipts are intentionally labeled `EXECUTED_NOT_INDEPENDENTLY_VERIFIED`.

## Evidence integrity

`FILE_HASHES.sha256` hashes code, tests and screenshot files. Source archive has no customer data and no secrets. `fixture_receipt.json` is an actual local fixture execution receipt; hashes bind code/evidence to the plan but do not authenticate a remote agent's identity.

## Next release gate

Independent Claude/Zane clean-checkout verification, network sandbox analysis, canonical Genesis approval integration, and a true authorized website roundtrip. Until then the browser is a local product prototype, not an autonomous operator.
