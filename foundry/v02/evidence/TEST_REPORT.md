# Genesis Foundry v0.2 — local test evidence

- Environment: Python 3.13.5, Chromium 144.0.7559.96, Playwright for Python, Linux x86-64. Production runtime uses Python standard library only.
- Unit/API: `PYTHONPATH=. python3 -W error::ResourceWarning -m unittest discover -s tests -v`: **18 passed, 0 errors** (Oct 9 2026). Includes create/read, stage updates, version conflict, SQLite restart persistence, integer-cent quotes, duplicate idempotency, invalid input, synthetic seed, JSON/CSV export, CSV injection protection, protected network bind, authenticated real HTTP request flow, cross-origin denial, atomic restore, no-overwrite, bad-restore rollback, and authenticated HTTP restore.
- Visual/browser: Chromium + Playwright `python3 tests/browser_smoke.py` tested 1365px desktop and 390px mobile. **6 test phases passed**: each viewport seed/list, quote edit/preview, new-lead form/overflow/no JS errors. `desktop.png` and `mobile.png` are output screenshots created with **synthetic fixture data only**.
- Browser network limitation: Chromium in the execution environment returns `ERR_BLOCKED_BY_ADMINISTRATOR` for all actual URLs, including 127.0.0.1. Therefore the browser UI smoke uses a JavaScript fake-fetch adapter. Real backend request flows were independently exercised by the Python HTTP integration tests. **Full browser-to-real-server E2E remains unverified.**
- CI run from clean GitHub checkout: **NOT YET DONE**.
- Independent review: **NOT YET DONE**.
- Customer interviews, sales, revenue: **NONE VERIFIED**.
- Auto agent or model execution: **NOT IMPLEMENTED**.
- Live hosting of v0.2: **NOT DEPLOYED**.

Never conflate static v0.1 website output, an AI plan, a staged message, or a passing mocked browser test with a verified autonomous app-builder run.
