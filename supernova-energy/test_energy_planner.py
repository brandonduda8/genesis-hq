import unittest
from energy_planner import Budget, Job, plan

class EnergyTests(unittest.TestCase):
    def test_battery_reserve(self):
        b=Budget(0,0,10,10,0.9,20)
        self.assertEqual(plan(b,[Job("train",20,1,10)])["selected_jobs"],[])
    def test_solar_and_battery_losses(self):
        self.assertAlmostEqual(Budget(10,20,30,10,.8,100).available_wh(),46)
    def test_no_energy_overdraft(self):
        self.assertEqual(plan(Budget(0,0,0,0,1,50),[Job("x",10,1,10)])["scheduled_wh"],0)
    def test_peak_power_limit(self):
        self.assertEqual(plan(Budget(100,0,0,0,1,20),[Job("x",25,1,10)])["selected_jobs"],[])
    def test_selection(self):
        result=plan(Budget(30,0,0,0,1,50),[Job("a",20,1,6),Job("b",30,1,8)])
        self.assertEqual(result["selected_jobs"],["b"])
    def test_bad_efficiency(self):
        with self.assertRaises(ValueError): Budget(1,0,0,0,1.5,20).available_wh()
    def test_duplicate(self):
        with self.assertRaises(ValueError): plan(Budget(100,0,0,0,1,20),[Job("x",10,1,1),Job("x",10,1,1)])
    def test_no_claim_live(self):
        self.assertEqual(plan(Budget(1,0,0,0,1,20),[])["state"],"SIMULATION_ONLY")

if __name__=="__main__": unittest.main()
