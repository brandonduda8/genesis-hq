"""Genesis Pay ONE: local round-up and portfolio proposal simulator.

Does not issue cards, connect banks, access a brokerage, invest, transfer,
report credit, or create a verified payment ledger. All event data is synthetic.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

TOKEN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,79}$")
SYMBOL = re.compile(r"^[A-Z][A-Z0-9._:-]{0,24}$")


def _token(value: str, key: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError(f"invalid {key}")
    return value


def _positive_cents(value: int, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= 100_000_000:
        raise ValueError(f"invalid {key}: positive integer cents required")
    return value


def _nonnegative_cents(value: int, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100_000_000:
        raise ValueError(f"invalid {key}: nonnegative integer cents required")
    return value


def roundup_cents(amount_cents: int) -> int:
    """Nearest next whole dollar; no forced roundup for exact dollar buys."""
    _positive_cents(amount_cents, "amount_cents")
    return (100 - amount_cents % 100) % 100


def propose_allocations(notional_cents: int, weights: Mapping[str, int]) -> dict[str, int]:
    """Split simulated notional amounts by *user-supplied* whole-percent weights.

    This does not make investment recommendations or place orders. A brokerage
    partner must validate the instruments, trade minimums and account status.
    """
    _positive_cents(notional_cents, "notional_cents")
    if not isinstance(weights, Mapping) or not 1 <= len(weights) <= 10:
        raise ValueError("invalid user allocations")
    entries = []
    for name, percent in weights.items():
        if not isinstance(name, str) or not SYMBOL.fullmatch(name):
            raise ValueError("invalid instrument alias")
        if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
            raise ValueError("invalid whole-percent weight")
        entries.append((name, percent))
    if sum(p for _, p in entries) != 100:
        raise ValueError("allocation weights must total 100")
    amounts = {name: (notional_cents * percent) // 100 for name, percent in entries}
    remainder = notional_cents - sum(amounts.values())
    order = sorted(entries, key=lambda x: (-(notional_cents * x[1] % 100), x[0]))
    for i in range(remainder):
        amounts[order[i][0]] += 1
    return dict(sorted(amounts.items()))


@dataclass(frozen=True)
class RoundupPolicy:
    minimum_sweep_cents: int = 500
    maximum_sweep_cents: int = 2500
    reserve_cents: int = 5000
    opt_in: bool = False

    def validate(self) -> None:
        _positive_cents(self.minimum_sweep_cents, "minimum_sweep_cents")
        _positive_cents(self.maximum_sweep_cents, "maximum_sweep_cents")
        _nonnegative_cents(self.reserve_cents, "reserve_cents")
        if self.maximum_sweep_cents < self.minimum_sweep_cents:
            raise ValueError("sweep maximum smaller than minimum")
        if not isinstance(self.opt_in, bool):
            raise ValueError("explicit opt_in boolean required")


class RoundupLab:
    """Durable local *simulated* event cache; NOT the production financial ledger.

    This demo never reads card PANs, bank details, real transaction webhooks,
    cardholder PII, credentials, exchange prices, or financial balances.
    """

    def __init__(self, filename: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(filename), isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("""CREATE TABLE IF NOT EXISTS purchases (
            purchase_id TEXT PRIMARY KEY,
            amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
            roundup_cents INTEGER NOT NULL CHECK(roundup_cents BETWEEN 0 AND 99),
            refunded_cents INTEGER NOT NULL DEFAULT 0,
            hold_for_review INTEGER NOT NULL DEFAULT 0 CHECK(hold_for_review IN (0,1))
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_kind TEXT NOT NULL CHECK(event_kind IN ('settlement', 'refund')),
            purchase_id TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            FOREIGN KEY(purchase_id) REFERENCES purchases(purchase_id)
        )""")

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _fingerprint(kind: str, purchase_id: str, amount_cents: int) -> str:
        payload = json.dumps([kind, purchase_id, amount_cents], separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def settle(self, event_id: str, purchase_id: str, amount_cents: int) -> dict:
        """Record a *synthetic* posted purchase, never an authorization hold."""
        _token(event_id, "event_id")
        _token(purchase_id, "purchase_id")
        amount_cents = _positive_cents(amount_cents, "amount_cents")
        fp = self._fingerprint("settlement", purchase_id, amount_cents)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT event_hash FROM events WHERE event_id=?", (event_id,)).fetchone()
            if old:
                if old["event_hash"] != fp:
                    raise ValueError("event_id replay with changed payload")
                duplicate = True
            else:
                if self.db.execute("SELECT 1 FROM purchases WHERE purchase_id=?", (purchase_id,)).fetchone():
                    raise ValueError("purchase already settled with different event")
                self.db.execute("INSERT INTO purchases(purchase_id,amount_cents,roundup_cents) VALUES(?,?,?)",
                                (purchase_id,amount_cents,roundup_cents(amount_cents)))
                self.db.execute("INSERT INTO events VALUES(?,?,?,?)",(event_id,"settlement",purchase_id,fp))
                duplicate = False
            r = self.db.execute("SELECT * FROM purchases WHERE purchase_id=?", (purchase_id,)).fetchone()
            self.db.execute("COMMIT")
            return {"state":"SIMULATED_SETTLEMENT_ONLY", "purchase_id":purchase_id,
                    "roundup_cents":r["roundup_cents"], "duplicate":duplicate,
                    "held_for_refund_review":bool(r["hold_for_review"])}
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def refund(self, event_id: str, purchase_id: str, amount_cents: int) -> dict:
        """A refund freezes its source roundup for review, not an auto-sell."""
        _token(event_id,"event_id")
        _token(purchase_id,"purchase_id")
        amount_cents=_positive_cents(amount_cents,"amount_cents")
        fp=self._fingerprint("refund",purchase_id,amount_cents)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old=self.db.execute("SELECT event_hash FROM events WHERE event_id=?",(event_id,)).fetchone()
            if old:
                if old["event_hash"] != fp:
                    raise ValueError("event_id replay with changed payload")
                duplicate=True
            else:
                r=self.db.execute("SELECT amount_cents,refunded_cents FROM purchases WHERE purchase_id=?",(purchase_id,)).fetchone()
                if not r:
                    raise ValueError("unknown purchase requires reconciliation")
                if amount_cents + r["refunded_cents"] > r["amount_cents"]:
                    raise ValueError("refund exceeds purchase")
                self.db.execute("UPDATE purchases SET refunded_cents=refunded_cents+?,hold_for_review=1 WHERE purchase_id=?",
                                (amount_cents,purchase_id))
                self.db.execute("INSERT INTO events VALUES(?,?,?,?)",(event_id,"refund",purchase_id,fp))
                duplicate=False
            self.db.execute("COMMIT")
            return {"state":"REFUND_REQUIRES_RECONCILIATION", "purchase_id":purchase_id,
                    "auto_liquidation":False, "duplicate":duplicate}
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def snapshot(self) -> dict:
        row=self.db.execute("""SELECT COALESCE(SUM(CASE WHEN hold_for_review=0 THEN roundup_cents ELSE 0 END),0) AS eligible,
            COALESCE(SUM(CASE WHEN hold_for_review=1 THEN roundup_cents ELSE 0 END),0) AS held,
            COUNT(*) AS purchases FROM purchases""").fetchone()
        return {"state":"SIMULATION_ONLY", "eligible_roundups_cents":row["eligible"],
                "held_for_review_cents":row["held"],"simulated_purchases":row["purchases"],
                "actual_invested_cents":0,"actual_card_issued":False}

    def propose_sweep(self, policy: RoundupPolicy, spendable_cash_cents: int,
                      user_allocations: Mapping[str,int] | None = None) -> dict:
        """Prepare a fictional batch proposal; NEVER move cash or place trades."""
        policy.validate()
        _nonnegative_cents(spendable_cash_cents,"spendable_cash_cents")
        snap=self.snapshot()
        reasons=[]
        if not policy.opt_in:
            reasons.append("CUSTOMER_OPT_IN_REQUIRED")
        total=snap["eligible_roundups_cents"]
        if total < policy.minimum_sweep_cents:
            reasons.append("BELOW_MINIMUM")
        amount=min(total,policy.maximum_sweep_cents)
        if spendable_cash_cents - policy.reserve_cents < amount:
            reasons.append("CASH_RESERVE_PROTECTION")
        if user_allocations is None:
            reasons.append("USER_ALLOCATION_REQUIRED")
            allocation=None
        else:
            allocation=propose_allocations(amount,user_allocations) if amount>0 else None
        if reasons:
            return {"state":"BLOCKED_NO_TRANSFER", "reasons":reasons,
                    "eligible_roundups_cents":total,"simulated_transfer":False,"live_trade":False}
        return {"state":"PAPER_PROPOSAL_ONLY", "amount_cents":amount,
                "proposed_allocations_cents":allocation,
                "requires_broker_KYC_and_user_authorization":True,
                "simulated_transfer":False,"live_trade":False}


if __name__=="__main__":
    lab=RoundupLab()
    for i, n in enumerate((735, 1210, 2000, 850, 620, 545, 330, 120, 101), start=1):
        lab.settle(f"demo-event-{i}",f"demo-purchase-{i}",n)
    print(json.dumps({"snapshot":lab.snapshot(),"plan":lab.propose_sweep(
        RoundupPolicy(opt_in=True), 25_000,{"DEMO_ETF_A":80,"DEMO_ETF_B":20})},indent=2))
