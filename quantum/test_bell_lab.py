import math
import unittest
from quantum.bell_lab import apply_cnot_first_control, apply_h_first, bell_state, probabilities

class QuantumForgeTests(unittest.TestCase):
    def test_bell_probabilities(self):
        p = probabilities(bell_state())
        self.assertAlmostEqual(p[0], 0.5)
        self.assertAlmostEqual(p[1], 0.0)
        self.assertAlmostEqual(p[2], 0.0)
        self.assertAlmostEqual(p[3], 0.5)

    def test_normalization(self):
        self.assertAlmostEqual(sum(probabilities(bell_state())), 1)

    def test_hadamard_is_its_own_inverse(self):
        x = (1+0j,0j,0j,0j)
        y = apply_h_first(apply_h_first(x))
        for a,b in zip(x,y):
            self.assertAlmostEqual(abs(a-b),0)

    def test_cnot_is_its_own_inverse(self):
        x = (1+0j,2+0j,3+0j,4+0j)
        self.assertEqual(apply_cnot_first_control(apply_cnot_first_control(x)),x)

if __name__ == '__main__':
    unittest.main()
