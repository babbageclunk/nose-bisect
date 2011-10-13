import logging
import os
import types
from unittest import TestSuite

from nose.plugins import Plugin
from nose.suite import ContextSuite, ContextSuiteFactory

log = logging.getLogger('nose.plugins.bisect')

def flatten_suite(suite):
    for child in suite:
        if isinstance(child, TestSuite):
            for gchild in flatten_suite(child):
                yield gchild
        else:
            yield child

def fractional_slice(items, lower, upper):
    count = len(items)
    return items[int(lower * count):int(upper * count)]

def dump_tree(item, indent=0, tests=False):
    spaces = ' ' * indent
    if not isinstance(item, ContextSuite):
        print spaces, item
        return
    print spaces, item
    for child in item:
        dump_tree(child, indent + 2, tests)

class Node(object):

    def __init__(self, context):
        self.context = context
        self.children = {}
        self.tests = []

    def add_context(self, path, context):
        if len(path) == 0:
            # It must be me!
            return self
        head = path[0]
        tail = path[1:]
        try:
            node = self.children[head]
        except KeyError:
            # This path wasn't found in the tree.
            assert not tail, 'Saw context {0} without seeing ancestors first'.format(context)
            node = self.children[head] = Node(context)
            return node
        else:
            return node.add_context(tail, context)

    def add_test(self, test):
        self.tests.append(test)

    def dump(self, depth=0):
        spaces = ' ' * (depth * 2)
        for name, child in sorted(self.children.items()):
            print spaces, name, '->', child.context
            child.dump(depth + 1)
        for test in self.tests:
            print spaces, test

    def to_context_suite(self):
        tests = []
        for _, child in sorted(self.children.items()):
            tests.append(child.to_context_suite())
        tests.extend(self.tests)
        return ContextSuite(tests, self.context)

def get_path(item):
    return full_path(item).split('.')

def full_path(item):
    if isinstance(item, (type, types.ClassType)):
        # Include the module name in the full path.
        return '{0}.{1}'.format(item.__module__, item.__name__)
    return item.__name__

def rebuild_context_suite(tests):
    "Construct a tree of ContextSuites from the tests-with-contexts passed in."
    factory = ContextSuiteFactory()
    all_ancestors = set()
    for test in tests:
        all_ancestors.update(factory.ancestry(test.context))

    root = Node(None)
    for ancestor in sorted(all_ancestors, key=full_path):
        root.add_context(get_path(ancestor), ancestor)

    for test in tests:
        node = root.add_context(get_path(test.context), test.context)
        node.add_test(test)

    return root.to_context_suite()

class Bisector(Plugin):
    name = 'bisect'

    def options(self, parser, env=os.environ):
        super(Bisector, self).options(parser, env=env)
        parser.add_option('--bisect-canary', dest='bisect_canary', action='store', default=None,
                          help='Test to run after slicing the suite from lower- '
                          'to upper-bound.')
        parser.add_option('--bisect-lower', dest='bisect_lower', action='store',
                          default=0, type=float,
                          help='Lower bound of current bisection pass, as '
                          'fraction of all tests (before the canary). (Default: 0)')
        parser.add_option('--bisect-upper', dest='bisect_upper', action='store',
                          default=1.0, type=float,
                          help='Upper bound of current bisection pass, as '
                          'fraction of all tests (before the canary). (Default: 1)')

    def configure(self, options, conf):
        super(Bisector, self).configure(options, conf)
        if not self.enabled:
            return
        self.canary_name = options.bisect_canary
        if not self.canary_name:
            conf.parser.error('--bisect-canary test name required')
        self.lower = options.bisect_lower
        self.upper = options.bisect_upper

    def prepareTest(self, test):
        all_tests = list(flatten_suite(test))
        preceding_tests = []
        canary = None
        for single_test in all_tests:
            if single_test.id() == self.canary_name:
                canary = single_test
                break
            preceding_tests.append(single_test)
        assert canary, 'Canary test {0} not found'.format(self.canary_name)

        candidates = fractional_slice(preceding_tests, self.lower, self.upper)
        candidates.append(canary)
        result = rebuild_context_suite(candidates)
        return result
