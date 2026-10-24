# Genesis Pay ONE | Local concept kit

**DEMO ONLY - NO CARD IS ISSUED - NO REAL INVESTMENT OR FINANCIAL DATA.**

- Open `demo.html` locally for an interactive concept display with sample spending and simulated investment proposals.
- Run `python3 -m unittest discover -s tests -v` from this directory for the deterministic round-up prototype tests.
- Run `python3 -m genesis_pay_one.engine` for a sample terminal calculation.
- Read `PRODUCT_SPEC.md` for the partnership, finance, compliance and feature roadmap.

The Python engine simulates settled purchases and refund holds, requires opt-in and user-selected percentages, respects a cash reserve, generates paper proposals, and refuses auto trade/transfer issuance. Its SQLite cache is NOT a production payment ledger. No real integrations, banking secrets or keys are used.
