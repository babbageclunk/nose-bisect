"""
Run nosetests with bisection repeatedly until only two tests are run,
and the canary is failing.
"""

from argparse import ArgumentParser
from collections import namedtuple
import re
from subprocess import Popen, PIPE
import sys

def run_nose(canary, interval, verbose=False):
    nose_cmd = ['nosetests', '--with-bisect',
                '--bisect-canary={0}'.format(canary),
                '--bisect-lower={0}'.format(interval[0]),
                '--bisect-upper={0}'.format(interval[1])]
    if verbose:
        nose_cmd.append('-v')
    print '*' * 80
    print ' '.join(nose_cmd)
    print
    return Popen(nose_cmd, stderr=PIPE)

PATTERNS = dict(
    count = re.compile(r'^Ran (\d+) test'),
    errors = re.compile(r'^FAILED.*errors=(\d+).*'),
    failures = re.compile(r'^FAILED.*failures=(\d+).*')
    )

RunResult = namedtuple('RunResult', 'passed tests errors fails')

def run_test_pass(canary, interval, verbose):
    process = run_nose(canary, interval, verbose)
    # Collect the last 3 lines of stderr output to determine how many
    # tests were run, and how many failed.
    found = {}
    for line in process.stderr:
        for name, pattern in PATTERNS.items():
            match = pattern.match(line)
            if match:
                if name in found:
                    raise Exception('Found too many {0} lines'.format(name))
                found[name] = int(match.group(1))
        sys.stderr.write(line)
    return_code = process.wait()
    result = RunResult(return_code == 0,
                       *[found.get(name, 0) for name in sorted(PATTERNS)])
    print result
    print
    return result

def bisect((lower, upper)):
    mid = (upper + lower) / 2.0
    return (lower, mid), (mid, upper)

def main(args):
    interval = 0.0, 1.0
    verbose = False
    while True:
        # Start by trying the lower interval.
        low_interval, high_interval = bisect(interval)

        result = run_test_pass(args.canary, low_interval, verbose)
        if result.tests == 2:
            break

        if args.sanity_check:
            result2 = run_test_pass(args.canary, high_interval, verbose)
            if result.passed and result2.passed:
                print 'Sanity check failed: both halves of the test suite passed.'
                break
            elif not result.passed and not result2.passed:
                print 'Sanity check failed: both halves of the test suite failed.'
                break

        interval = low_interval if not result.passed else high_interval
        if result.tests <= 10:
            verbose = True

parser = ArgumentParser(description='Bisect test suite to find the test causing canary to die.')
parser.add_argument('-s', '--sanity-check', action='store_true', default=False,
                    help='Run both sides of each bisection to check that both sides '
                    'don\'t fail (or pass).')
parser.add_argument('canary', metavar='CANARY', help='The test that is being broken.')

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)
