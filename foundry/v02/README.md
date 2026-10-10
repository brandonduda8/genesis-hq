# Genesis Foundry v0.2 — Lead-to-Quote Workspace

**A real, local-first small-business software prototype.** Capture leads, update stages, draft service quotes, and keep durable customer records. Built with the Python standard library and SQLite; no paid model, external service, or account required to run locally.

The user owns the source code and local records. This is **not** an autonomous AI agent, invoice service, CRM with customer communication, or a production-ready SaaS deployment.

## What works

- Mobile-friendly dashboard showing lead stages and estimated quote pipeline (not realized revenue).
- Lead intake and editing with validation, version checks and duplicate-request protection.
- Quote item editor with server-calculated totals in **integer cents**, editable line items and safe limits.
- SQLite WAL data on disk, event receipts, persistence after restart.
- JSON backups with **atomic restore into an empty workspace only**, and CSV spreadsheet exports with formula-injection mitigation.
- Synthetic sample records loaded on demand and clearly labeled.
- No email, billing, payments, outreach, remote model execution or agent automation.
- Local-only default binding; remote binding requires a strong owner token. A reverse proxy with HTTPS and stronger identity/rate limits is needed before any public or customer deployment.

## Run (for engineering operators)

Prerequisite: Python 3.11+; no pip install required.

```sh
python3 -m foundry_v02.server
```

Open `http://127.0.0.1:8787` in a browser on the **same machine**. Storage defaults to `~/.genesis/foundry.sqlite`. To specify a separate file:

```sh
python3 -m foundry_v02.server --db /path/to/owned-data/foundry.sqlite --port 8787
```

The sqlite database and its WAL/SHM files are local state, NOT included in the source archive. They should remain private. Use **Backup JSON** for a portable copy of all stored leads. **Import JSON** is only available when no leads exist; it validates every item and commits atomically without overwriting active data. The current import supports up to 2000 records and 900 KB per browser upload. CSV is for human-readable spreadsheets, not restoration.

### Private-network deployments

Binding other than loopback requires a secret `FOUNDRY_OWNER_TOKEN` of at least 32 characters, set only in the host secret store, and an explicitly owner-approved deployment. **Never pass this token to GitHub, logs, or a chat message. Use HTTPS and a private ingress.** Tokens typed into the page remain in that tab's memory; clear the tab after use.

Render's **free** web-service filesystem is ephemeral, so do **not** deploy this SQLite application there with real customer records. The existing Render HQ remains separate. For demonstrations on Render, use only synthetic data or a properly provisioned persistent datastore after review and approval.

## Verification

```sh
python3 -m unittest discover -s tests -p 'test_foundry.py' -v
```

The optional Chromium smoke test uses a **simulated browser API** because the isolated test environment blocks browser navigation. It does verify the real UI event handlers, responsiveness and quote editor, but does not replace live end-to-end testing on an actual deployed site:

```sh
python3 tests/browser_smoke.py
```

`evidence/TEST_REPORT.md` records the exact local results and limitations. No independent Claude review or production security assessment has yet been completed.

## Data and privacy

- All records are local, including names and email addresses. For demos, use the built-in synthetic records.
- A quote is a **draft estimate**, not a legally binding invoice. This release does not calculate tax, accept signatures, or transmit customer information.
- Never enter real customer data into a publicly exposed free demo. Always get a customer's permission before importing their data.
- Version conflicts respond with HTTP 409 rather than silently overwrite another editor's changes.
- No automatic sends or background workers.

## Product direction

The next milestone is Genesis Foundry's approved job pipeline: objective -> authorized specification -> actual worker -> portable artifact -> independent verifier -> downloadable proof. That workflow is **not** implemented in this v0.2 app. This release is valuable on its own as a functional lead-to-quote tool and proof that Genesis can ship software.

Related tracker: https://github.com/brandonduda8/genesis-hq/issues/3
