from nose.suite import ContextSuite
from unittest import TestCase, TestSuite

from nose_bisect import (
    flatten_suite, fractional_slice, Node
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

class ArbitraryTest(TestCase):
    """Acts as if it has all possible test method names."""
    def __getattr__(self, name):
        return lambda _: None

class NodeTests(TestCase):

    def test_construction(self):
        thing = object()
        n = Node(thing)
        self.assertEqual(n.context, thing)
        self.assertEqual(n.children, {})
        self.assertEqual(n.tests, [])

    def test_add_context_no_path(self):
        n = Node(None)
        self.assertEqual(n.add_context([], None), n)

    def test_add_context_adds_child(self):
        n1 = Node('parent')
        n2 = n1.add_context(['path'], 'child')
        self.assertEqual(n1.children['path'], n2)
        self.assertEqual(n2.context, 'child')

    def test_add_context_returns_existing(self):
        n1 = Node('parent')
        n2 = n1.add_context(['path'], 'child')
        n3 = n1.add_context(['path'], 'whatever')
        self.assertEqual(n3, n2)

    def test_add_context_finds_right_position(self):
        n1 = Node('parent')
        n2 = n1.add_context(['path'], 'child')
        n3 = n1.add_context(['path','to'], 'grandchild')
        self.assertEqual(n2.children, {'to': n3})
        self.assertEqual(n3.context, 'grandchild')

    def test_add_test(self):
        n = Node('node')
        n.add_test('whatever')
        self.assertEqual(n.tests, ['whatever'])

    def test_to_context_suite(self):
        def add_test(node, val):
            node.add_test(ArbitraryTest(str(val)))

        tree = Node(None)
        add_test(tree, 1)
        add_test(tree, 2)
        for i in range(3):
            name = 'a' + str(i)
            n = tree.add_context([name], name)
            add_test(n, name)
        level3 = tree.add_context(['a1', 'c'], 'c')
        add_test(level3, 'l3')
        csuite = tree.to_context_suite()

        def collapse_csuite(csuite):
            result = []
            for thing in csuite:
                if isinstance(thing, ContextSuite):
                    item = (thing.context, collapse_csuite(thing))
                else:
                    item = thing.id().split('.')[-1]
                result.append(item)
            return result
        result = collapse_csuite(csuite)
        expected = [
            ('a0', ['a0']),
            ('a1', [
                ('c', ['l3']),
                'a1'
            ]),
            ('a2', ['a2']),
            '1',
            '2']
        self.assertEqual(result, expected)
