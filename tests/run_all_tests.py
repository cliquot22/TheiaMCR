"""
Unified Test Runner for TheiaMCR
Runs fuzz tests, error propagation tests, and generates test report
"""

import unittest
import sys
import time
from datetime import datetime
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure the project root is on the import path so the package resolves correctly
sys.path.insert(0, PROJECT_ROOT)
import TheiaMCR as mcr


def get_mcr_revision():
    """Get the MCR revision number"""
    try:
        return mcr.MCR_REVISION
    except AttributeError:
        return 'unknown'


def run_all_tests():
    """Run all tests and generate report"""
    
    print("="*70)
    print("TheiaMCR Comprehensive Test Suite")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"MCR Version: {get_mcr_revision()}")
    print("="*70)
    print()
    
    # Discover and load all tests from the actual tests directory, not the workspace root
    loader = unittest.TestLoader()
    start_dir = TESTS_DIR
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Count tests
    test_count = suite.countTestCases()
    print(f"Found {test_count} tests across all test files")
    print()
    
    # Capture the test IDs before the runner consumes the suite so the report can list them reliably
    executed_test_ids = [case.id() for case in collect_test_cases(suite)]

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    elapsed_time = time.time() - start_time
    
    # Generate summary
    print()
    print("="*70)
    print("TEST SUMMARY")
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
    
    # Generate test report file
    report_filename = generate_test_report(result, elapsed_time, suite=suite, executed_tests=executed_test_ids)
    
    # Final status
    print("="*70)
    if result.wasSuccessful():
        print("[PASS] ALL TESTS PASSED")
        print(f"[PASS] Test report saved to: {report_filename}")
        return 0
    else:
        print("[FAIL] SOME TESTS FAILED")
        print(f"[FAIL] Test report saved to: {report_filename}")
        return 1


def get_product_revision_code(product_name='TheiaMCR'):
    """Return the CRA revision code for a product name."""
    codes = {
        'TheiaMCR': 'TR-002',
        'TheiaMCR_C': 'TR-003',
        'lensIQ': 'TR-004',
    }
    return codes.get(product_name, 'TR-000')


def normalize_version_for_filename(raw_version):
    """Convert version strings like 'v.3.5.1' to 'v3.5.1'."""
    if raw_version is None:
        return 'unknown'
    version = str(raw_version).strip()
    if version.lower().startswith('v.'):
        return 'v' + version[2:]
    if version.lower().startswith('v') and version[1:2] != '.':
        return version
    if version.lower().startswith('v.'):
        return 'v' + version[2:]
    return version if version.startswith('v') else f'v{version}'


def collect_test_cases(suite):
    """Flatten a unittest suite into individual test cases."""
    collected = []
    tests = getattr(suite, '_tests', [])
    for test in tests:
        if test is None:
            continue
        if isinstance(test, unittest.TestSuite):
            collected.extend(collect_test_cases(test))
        elif hasattr(test, 'id'):
            collected.append(test)
    return collected


def generate_test_report(result, elapsed_time, suite=None, executed_tests=None):
    """Generate a detailed Markdown test report with the executed tests listed."""
    timestamp = datetime.now().strftime('%Y-%m-%d')
    version = normalize_version_for_filename(get_mcr_revision())
    report_name = f"CRA-{get_product_revision_code()}_TheiaMCR_{version}_UnitTests_{timestamp}.md"
    filepath = os.path.join(os.path.dirname(__file__), report_name)

    bugs = analyze_bugs(result)
    success_count = result.testsRun - len(result.failures) - len(result.errors)
    pass_rate = (success_count / result.testsRun * 100) if result.testsRun > 0 else 0

    # Build an explicit list of the test functions that ran.
    if executed_tests is None:
        executed_tests = []
        if suite is not None:
            for case in collect_test_cases(suite):
                executed_tests.append(case.id())
        else:
            executed_tests = [str(test) for test, _ in result.failures + result.errors]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# TheiaMCR Test Report\n\n")

        if result.wasSuccessful():
            f.write("## ✅ ALL TESTS PASSED\n\n")
        else:
            f.write(f"## ⚠️ {len(result.failures) + len(result.errors)} Tests Failed\n\n")

        f.write("## 📊 Executive Summary\n\n")
        f.write(f"- **Report Name**: `{report_name}`\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Product**: TheiaMCR\n")
        f.write(f"- **Revision**: {get_product_revision_code()}\n")
        f.write(f"- **MCR Version**: {get_mcr_revision()}\n")
        f.write(f"- **Platform**: {sys.platform}\n")
        f.write(f"- **Total Tests**: {result.testsRun}\n")
        f.write(f"- **Passed**: {success_count} ✅\n")
        f.write(f"- **Failed**: {len(result.failures)} ❌\n")
        f.write(f"- **Errors**: {len(result.errors)} ⚠️\n")
        f.write(f"- **Skipped**: {len(result.skipped)} ⏭️\n")
        f.write(f"- **Pass Rate**: {pass_rate:.1f}%\n")
        f.write(f"- **Runtime**: {elapsed_time:.3f} seconds\n\n")

        f.write("## 🧪 Tests Executed\n\n")
        f.write("The following test functions were executed in this run:\n\n")
        for test_id in executed_tests:
            f.write(f"- `{test_id}`\n")
        f.write("\n")

        if bugs:
            f.write(f"## 🐛 Bugs Discovered ({len(bugs)})\n\n")
            for i, bug in enumerate(bugs, 1):
                f.write(f"### {i}. {bug['title']}\n\n")
                f.write(f"**Severity**: {bug['severity']}\n\n")
                f.write(f"**Issue**: {bug['description']}\n\n")
                if bug['tests']:
                    f.write("**Failing Tests**:\n")
                    for test in bug['tests']:
                        f.write(f"- `{test}`\n")
                    f.write("\n")
                if bug.get('details'):
                    f.write(f"**Details**: {bug['details']}\n\n")
                f.write(f"**Impact**: {bug['impact']}\n\n")
                f.write(f"**Recommendation**: {bug['recommendation']}\n\n")
        else:
            f.write("## ✅ No Bugs Detected\n\n")
            f.write("All tests passing! The code is working as expected.\n\n")

        if bugs:
            f.write("## 🎯 Priority Recommendations\n\n")
            critical_bugs = [b for b in bugs if b['severity'] == '🔴 Critical']
            high_bugs = [b for b in bugs if b['severity'] == '🟠 High']
            medium_bugs = [b for b in bugs if b['severity'] == '🟡 Medium']

            if critical_bugs:
                f.write("### Immediate Actions (Critical)\n\n")
                for bug in critical_bugs:
                    f.write(f"1. **{bug['title']}** - {bug['recommendation']}\n")
                f.write("\n")
            if high_bugs:
                f.write("### High Priority\n\n")
                for bug in high_bugs:
                    f.write(f"- **{bug['title']}** - {bug['recommendation']}\n")
                f.write("\n")
            if medium_bugs:
                f.write("### Medium Priority\n\n")
                for bug in medium_bugs:
                    f.write(f"- {bug['title']}\n")
                f.write("\n")

        f.write("## 📋 Test Details\n\n")
        fuzz_tests = [t for t in result.failures + result.errors if 'fuzz' in str(t[0]).lower()]
        error_tests = [t for t in result.failures + result.errors if 'error' in str(t[0]).lower()]

        f.write("### Test Categories\n\n")
        f.write("| Category | Status | Count |\n")
        f.write("|----------|--------|-------|\n")
        f.write(f"| Fuzz Tests | {'✅' if not fuzz_tests else '⚠️'} | {0 if not fuzz_tests else len(fuzz_tests)} failed |\n")
        f.write(f"| Error Handling | {'✅' if not error_tests else '⚠️'} | {0 if not error_tests else len(error_tests)} failed |\n")
        f.write("\n")

        if result.failures:
            f.write("### ❌ Test Failures\n\n")
            for test, traceback in result.failures:
                f.write(f"#### {test}\n\n")
                f.write("```\n")
                f.write(traceback)
                f.write("```\n\n")

        if result.errors:
            f.write("### ⚠️ Test Errors\n\n")
            for test, traceback in result.errors:
                f.write(f"#### {test}\n\n")
                f.write("```\n")
                f.write(traceback)
                f.write("```\n\n")

        if result.skipped:
            f.write("### ⏭️ Skipped Tests\n\n")
            for test, reason in result.skipped:
                f.write(f"- **{test}**: {reason}\n")
            f.write("\n")

        if bugs:
            f.write("## 🔄 Next Steps\n\n")
            f.write("1. **Review Critical Bugs** - Address critical severity issues first\n")
            f.write("2. **Implement Fixes** - Apply recommended fixes for each bug\n")
            f.write("3. **Re-run Tests** - Verify fixes with `python run_all_tests.py`\n")
            f.write("4. **Update Documentation** - Document any API changes\n")
            f.write("5. **Track Progress** - Compare with previous test reports\n\n")
        else:
            f.write("## 🎉 Success!\n\n")
            f.write("All tests are passing. Consider:\n")
            f.write("1. Adding more edge case tests\n")
            f.write("2. Increasing test coverage\n")
            f.write("3. Adding integration tests\n\n")

        f.write("---\n\n")
        f.write(f"**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**MCR Version**: {get_mcr_revision()}\n\n")
        f.write("**Test Command**: `python run_all_tests.py`\n")

    print(f"\nDetailed test report saved to: {filepath}")
    return filepath


def analyze_bugs(result):
    """Analyze test failures and errors to categorize bugs"""
    bugs = []
    
    # Collect all test names
    failed_tests = [(str(test), traceback) for test, traceback in result.failures]
    error_tests = [(str(test), traceback) for test, traceback in result.errors]
    all_issues = failed_tests + error_tests
    
    if not all_issues:
        return bugs
    
    # Analyze patterns in failures
    indexerror_tests = [t for t, tb in all_issues if 'IndexError' in tb]
    assertion_tests = [t for t, tb in all_issues if 'AssertionError' in tb]
    typeerror_tests = [t for t, tb in all_issues if 'TypeError' in tb]
    
    # Bug 1: IndexError in functions
    if indexerror_tests:
        bugs.append({
            'title': 'IndexError in Response Parsing',
            'severity': '🔴 Critical',
            'description': 'Functions crash when accessing array indices without checking response length first.',
            'tests': indexerror_tests,
            'details': 'Error responses are shorter than expected, causing IndexError when code tries to access response[1] or other indices.',
            'impact': 'Application crashes when communication errors occur. No graceful error handling.',
            'recommendation': 'Add response length validation before accessing indices. Check `if len(response) >= expected_length` before parsing.'
        })
    
    # Bug 2: Position tracking issues
    position_tests = [t for t, tb in all_issues if 'currentStep' in tb or 'position' in t.lower()]
    if position_tests:
        bugs.append({
            'title': 'Motor Position Tracking Errors',
            'severity': '🟠 High',
            'description': 'currentStep may be updated even when motor move fails.',
            'tests': position_tests,
            'impact': 'Position tracking becomes incorrect after failed moves, requiring re-homing.',
            'recommendation': 'Only update currentStep after verifying move success. Check return value before updating position.'
        })
    
    # Bug 3: Error propagation
    error_prop_tests = [t for t, tb in all_issues if 'error' in t.lower() and 'ERR_OK' in tb]
    if error_prop_tests:
        bugs.append({
            'title': 'Inconsistent Error Propagation',
            'severity': '🟠 High',
            'description': 'Some functions return success (ERR_OK) even when underlying operations fail.',
            'tests': error_prop_tests,
            'impact': 'Application cannot detect failures, leading to silent errors and incorrect state.',
            'recommendation': 'Review error checking in motor functions. Ensure all failure paths return appropriate error codes.'
        })
    
    # Bug 4: Missing error logging
    logging_tests = [t for t, tb in all_issues if 'finalError' in tb or 'logged' in t.lower()]
    if logging_tests:
        bugs.append({
            'title': 'Errors Not Logged to finalError',
            'severity': '🟡 Medium',
            'description': 'Errors are not being saved to err.finalError list for debugging.',
            'tests': logging_tests,
            'impact': 'Difficult to diagnose problems after they occur. No error history available.',
            'recommendation': 'Ensure err.saveError() is called in all error paths. Verify error list is being populated.'
        })
    
    # Bug 5: Type errors in function signatures
    if typeerror_tests:
        bugs.append({
            'title': 'Function Signature Mismatch',
            'severity': '🟡 Medium',
            'description': 'Function being called with parameters that don\'t match signature.',
            'tests': typeerror_tests,
            'details': 'Check for deprecated parameters or signature changes.',
            'impact': 'Functions cannot be called correctly, causing runtime errors.',
            'recommendation': 'Review function signatures and update call sites. Remove deprecated parameters or update documentation.'
        })
    
    # Bug 6: General assertion failures
    # Find assertion tests not already categorized
    categorized_tests = [bug_test for bug in bugs for bug_test in bug.get('tests', [])]
    other_assertions = [t for t in assertion_tests if t not in categorized_tests]
    if other_assertions:
        bugs.append({
            'title': 'Test Assertion Failures',
            'severity': '🟡 Medium',
            'description': 'Functions not behaving as expected based on test assertions.',
            'tests': other_assertions[:5],  # Limit to first 5
            'impact': 'Code behavior differs from expected behavior documented in tests.',
            'recommendation': 'Review each failing test and verify expected behavior. Update implementation or test expectations as needed.'
        })
    
    return bugs


def print_test_statistics():
    """Print test statistics by category"""
    print("\nTest Statistics by Category:")
    print("-"*70)
    
    # Count tests in each file
    loader = unittest.TestLoader()
    
    try:
        fuzz_suite = loader.loadTestsFromName('test_fuzz_sendCmd')
        fuzz_count = fuzz_suite.countTestCases()
        print(f"Fuzz Tests: {fuzz_count}")
    except:
        print("Fuzz Tests: N/A")
    
    try:
        error_suite = loader.loadTestsFromName('test_error_handling')
        error_count = error_suite.countTestCases()
        print(f"Error Propagation Tests: {error_count}")
    except:
        print("Error Propagation Tests: N/A")
    
    print()


if __name__ == '__main__':
    sys.exit(run_all_tests())
