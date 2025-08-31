#!/usr/bin/env python3
"""
Test runner script for KubeVirt AI agent tests.
"""

import sys
import unittest
from pathlib import Path

def run_tests():
    """Run all unit tests."""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / "tests"
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with non-zero code if tests failed
    if not result.wasSuccessful():
        sys.exit(1)

    print(f"\n✅ All tests passed! ({result.testsRun} tests)")

if __name__ == '__main__':
    run_tests()
