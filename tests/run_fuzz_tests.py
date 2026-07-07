"""
Fuzz Test Runner for TheiaMCR
Runs all fuzz tests with detailed output and summary
"""

import unittest
import sys
import time
from io import StringIO

def run_fuzz_tests():
    """Run all fuzz tests and provide detailed summary"""
    
    print("="*70)
    print("TheiaMCR Fuzz Test Suite")
    print("Testing _sendCmd robustness against malformed inputs/outputs")
    print("="*70)
    print()
    
    # Discover and load tests
    loader = unittest.TestLoader()
    start_dir = '.'
    suite = loader.discover(start_dir, pattern='test_fuzz*.py')
    
    # Count tests
    test_count = suite.countTestCases()
    print(f"Found {test_count} fuzz tests")
    print()
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    elapsed_time = time.time() - start_time
    
    # Print summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Time elapsed: {elapsed_time:.3f} seconds")
    print()
    
    # Show failures if any
    if result.failures:
        print("FAILURES:")
        print("-"*70)
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    # Show errors if any
    if result.errors:
        print("ERRORS:")
        print("-"*70)
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    # Final status
    print("="*70)
    if result.wasSuccessful():
        print("[PASS] ALL TESTS PASSED")
        print("[PASS] _sendCmd is robust against fuzz inputs")
        return 0
    else:
        print("[FAIL] SOME TESTS FAILED")
        print("[FAIL] Review failures above and fix _sendCmd implementation")
        return 1

if __name__ == '__main__':
    sys.exit(run_fuzz_tests())
