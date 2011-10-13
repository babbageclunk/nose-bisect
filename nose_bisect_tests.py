from unittest import TestCase, TestSuite

from nose_bisect import (
    flatten_suite, fractional_slice
)

class BisectTests(TestCase):

    def test_flatten_suite(self):
        fake_tests = [lambda: x for x in range(4)]
        t1, t2, t3, t4 = fake_tests
        root = TestSuite([
            t1, TestSuite([t2, t3, TestSuite([t4])])])
        self.assertEqual(list(flatten_suite(root)), [t1, t2, t3, t4])

    def test_fractional_slice(self):
        f = fractional_slice
        items = range(10)
        self.assertEqual(f(items, 0, 1), range(10))
        self.assertEqual(f(items, 0, 0.5), range(5))
        self.assertEqual(f(items, 0.5, 1), range(5, 10))
        self.assertEqual(f(items, 0.1, 0.3), [1, 2])
