import math
import random
import unittest
from fractions import Fraction

from tools.oracle.surd import Surd


class SurdTest(unittest.TestCase):
    def test_perfect_squares_fold(self):
        self.assertEqual(Surd.sqrt(25, 3).t, {})
        self.assertEqual(Surd.sqrt(25, 3).a, 15)

    def test_sign_one_radical(self):
        self.assertEqual((Surd(3) - Surd.sqrt(2, 2)).sign(), 1)        # 3 > 2.828
        self.assertEqual((Surd(2) - Surd.sqrt(5)).sign(), -1)           # 2 < 2.236
        self.assertEqual((Surd(-7) + Surd.sqrt(48)).sign(), -1)         # 6.93 < 7

    def test_sign_two_radicals(self):
        self.assertEqual((Surd.sqrt(2) + Surd.sqrt(3) - Surd(Fraction(3146, 1000))).sign(), 1)
        self.assertEqual((Surd.sqrt(2) + Surd.sqrt(3) - Surd(Fraction(3147, 1000))).sign(), -1)
        # sqrt(8) - 2*sqrt(2) is exactly zero even though the radicands differ
        self.assertEqual((Surd.sqrt(8) - Surd.sqrt(2, 2)).sign(), 0)
        self.assertEqual((Surd(1) + Surd.sqrt(8) - Surd.sqrt(2, 2) - 1).sign(), 0)

    def test_sign_agrees_with_floats_far_from_zero(self):
        rnd = random.Random(7)
        for _ in range(3000):
            a = Fraction(rnd.randint(-10**6, 10**6), rnd.randint(1, 50))
            b = Fraction(rnd.randint(-10**4, 10**4), rnd.randint(1, 50))
            c = Fraction(rnd.randint(-10**4, 10**4), rnd.randint(1, 50))
            m, n = rnd.randint(2, 10**6), rnd.randint(2, 10**6)
            s = Surd(a, {m: b}) + Surd(0, {n: c})
            f = float(a) + float(b) * math.sqrt(m) + float(c) * math.sqrt(n)
            if abs(f) > 1e-6:
                self.assertEqual(s.sign(), 1 if f > 0 else -1, (a, b, m, c, n))

    def test_floor_and_round(self):
        self.assertEqual(Surd.sqrt(2).floor(), 1)
        self.assertEqual((-Surd.sqrt(2)).floor(), -2)
        self.assertEqual(Surd.sqrt(2, 1000000).round(), 1414214)
        self.assertEqual(Surd(Fraction(5, 2)).round(), 2)
        self.assertEqual(Surd(Fraction(7, 2)).round(), 4)
        self.assertEqual(Surd(Fraction(-5, 2)).round(), -2)
        self.assertEqual(Surd(Fraction(-3, 2)).round(), -2)

    def test_exact_tie_through_cancelling_radicals_rounds_to_even(self):
        # 5/2 + sqrt(8) - 2*sqrt(2) is exactly 5/2: a float evaluation lands a hair off the tie
        x = Surd(Fraction(5, 2)) + Surd.sqrt(8) - Surd.sqrt(2, 2)
        self.assertEqual(x.round(), 2)
        y = Surd(Fraction(7, 2)) + Surd.sqrt(18) - Surd.sqrt(2, 3)
        self.assertEqual(y.round(), 4)
        self.assertNotEqual(float(Surd(Fraction(7, 2)) + 0) + math.sqrt(18) - 3 * math.sqrt(2), 3.5)

    def test_near_tie_irrational(self):
        # 2.5 + (sqrt(10^12 + 1) - 10^6) is a hair above 2.5, so rounds to 3
        x = Surd(Fraction(5, 2) - 10**6) + Surd.sqrt(10**12 + 1)
        self.assertEqual(x.round(), 3)
        z = Surd(Fraction(5, 2) + 10**6) - Surd.sqrt(10**12 + 1)
        self.assertEqual(z.round(), 2)

    def test_product(self):
        p = (Surd(1) + Surd.sqrt(2)) * (Surd(1) - Surd.sqrt(2))
        self.assertEqual(p.sign(), -1)
        self.assertEqual(p, Surd(-1))


if __name__ == '__main__':
    unittest.main()
