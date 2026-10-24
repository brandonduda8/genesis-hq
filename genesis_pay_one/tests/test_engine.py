import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from genesis_pay_one.engine import RoundupLab, RoundupPolicy, roundup_cents, propose_allocations

class RoundupTests(unittest.TestCase):
    def setUp(self):
        self.lab=RoundupLab()
    def tearDown(self):
        self.lab.close()
    def test_purchase_rounds_to_next_dollar(self):
        self.assertEqual(roundup_cents(735),65)
        self.assertEqual(roundup_cents(1210),90)
    def test_whole_dollar_zero(self): self.assertEqual(roundup_cents(2000),0)
    def test_edge_1cent(self):
        self.assertEqual(roundup_cents(1),99)
        self.assertEqual(roundup_cents(99),1)
    def test_no_floating_point_or_bool(self):
        for value in (-1,0,12.5,True,False,2**62):
            with self.assertRaises(ValueError): roundup_cents(value)
    def test_settlement_only(self):
        got=self.lab.settle("e1","p1",735)
        self.assertEqual(got['state'],'SIMULATED_SETTLEMENT_ONLY')
        self.assertEqual(self.lab.snapshot()['actual_invested_cents'],0)
    def test_duplicate_event_idempotent(self):
        first=self.lab.settle("e1","p1",735)
        second=self.lab.settle("e1","p1",735)
        self.assertEqual(first['roundup_cents'],second['roundup_cents'])
        self.assertTrue(second['duplicate'])
        self.assertEqual(self.lab.snapshot()['simulated_purchases'],1)
    def test_changed_replay_rejected(self):
        self.lab.settle("e1","p1",735)
        with self.assertRaisesRegex(ValueError,'changed payload'):
            self.lab.settle("e1","p1",730)
    def test_duplicate_purchase_separate_event_rejected(self):
        self.lab.settle("e1","p1",735)
        with self.assertRaises(ValueError): self.lab.settle("e2","p1",735)
    def test_refund_holds_roundup(self):
        self.lab.settle("e1","p1",735)
        res=self.lab.refund("r1","p1",200)
        self.assertFalse(res['auto_liquidation'])
        self.assertEqual(self.lab.snapshot()['held_for_review_cents'],65)
        self.assertEqual(self.lab.snapshot()['eligible_roundups_cents'],0)
    def test_duplicate_refund_idempotent(self):
        self.lab.settle("e1","p1",735)
        self.lab.refund("r1","p1",200)
        second=self.lab.refund("r1","p1",200)
        self.assertTrue(second['duplicate'])
    def test_refund_above_settlement_rejected(self):
        self.lab.settle("e1","p1",735)
        with self.assertRaisesRegex(ValueError,'exceeds purchase'):
            self.lab.refund("r1","p1",736)
    def test_unknown_purchase_refund_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown purchase'):
            self.lab.refund("r1","p1",300)
    def test_refund_replay_tamper_rejected(self):
        self.lab.settle("e1","p1",735)
        self.lab.refund("r1","p1",200)
        with self.assertRaises(ValueError): self.lab.refund("r1","p1",201)
    def test_no_sweep_without_optin(self):
        self.lab.settle("e1","p1",101)
        r=self.lab.propose_sweep(RoundupPolicy(),10_000,{"DEMO":100})
        self.assertIn('CUSTOMER_OPT_IN_REQUIRED',r['reasons'])
    def test_threshold_blocks(self):
        self.lab.settle("e1","p1",735)
        r=self.lab.propose_sweep(RoundupPolicy(opt_in=True),10_000,{"DEMO":100})
        self.assertIn('BELOW_MINIMUM',r['reasons'])
    def test_reserve_blocks(self):
        for i in range(6):self.lab.settle(f"e{i}",f"p{i}",101)
        r=self.lab.propose_sweep(RoundupPolicy(opt_in=True),5_100,{"DEMO":100})
        self.assertIn('CASH_RESERVE_PROTECTION',r['reasons'])
    def test_no_allocations_blocks(self):
        for i in range(6):self.lab.settle(f"e{i}",f"p{i}",101)
        r=self.lab.propose_sweep(RoundupPolicy(opt_in=True),25_000)
        self.assertIn('USER_ALLOCATION_REQUIRED',r['reasons'])
    def test_valid_proposal_still_no_transfer(self):
        for i in range(6):self.lab.settle(f"e{i}",f"p{i}",101)
        r=self.lab.propose_sweep(RoundupPolicy(opt_in=True),25_000,{"DEMO_ETF_A":70,"DEMO_ETF_B":30})
        self.assertEqual(r['state'],'PAPER_PROPOSAL_ONLY')
        self.assertEqual(r['amount_cents'],594)
        self.assertEqual(sum(r['proposed_allocations_cents'].values()),594)
        self.assertFalse(r['live_trade'])
        self.assertFalse(r['simulated_transfer'])
    def test_investment_split_exact_remainder(self):
        x=propose_allocations(5,{"A":33,"B":33,"C":34})
        self.assertEqual(sum(x.values()),5)
        self.assertEqual(x,{"A":2,"B":1,"C":2})
    def test_allocation_reject_bad_weights(self):
        for x in ({"A":80,"B":10},{"A":True,"B":99},{"a":100},{"A":101}):
            with self.assertRaises(ValueError): propose_allocations(500,x)
    def test_event_store_survives_restart(self):
        with tempfile.TemporaryDirectory() as t:
            db=os.path.join(t,'roundup-demo.sqlite')
            a=RoundupLab(db);a.settle('e1','p1',735);a.close()
            b=RoundupLab(db)
            self.assertEqual(b.snapshot()['eligible_roundups_cents'],65)
            b.close()
    def test_no_credentials_or_broker_connectors(self):
        self.assertFalse(hasattr(self.lab,'execute_trade'))
        self.assertFalse(hasattr(self.lab,'issue_card'))
        self.assertFalse(hasattr(self.lab,'send_ach'))
    def test_reserve_policy_is_validated(self):
        with self.assertRaises(ValueError):RoundupPolicy(minimum_sweep_cents=500,maximum_sweep_cents=400,opt_in=True).validate()
    def test_maximum_sweep_limits_amount(self):
        for i in range(12):self.lab.settle(f"e{i}",f"p{i}",101)
        r=self.lab.propose_sweep(RoundupPolicy(opt_in=True,maximum_sweep_cents=600),25_000,{"DEMO":100})
        self.assertEqual(r['amount_cents'],600)
    def test_replayed_refund_same_event_cannot_be_other_kind(self):
        self.lab.settle('e1','p1',735)
        with self.assertRaises(ValueError):self.lab.refund('e1','p1',735)

if __name__ == '__main__': unittest.main()
