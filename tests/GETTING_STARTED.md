# TheiaMCR Testing - Quick Start Guide

## What Was Created

### 1. Fuzz Tests (`test_fuzz_sendCmd.py`)
- **25 tests** validating `_sendCmd()` robustness
- Tests command/response overruns, malformed data, exceptions
- ✅ **All 25 passing**

### 2. Error Propagation Tests (`test_error_handling.py`)
- **21 tests** checking how functions handle `_sendCmd()` failures
- Tests error response handling: `[0x74, 0x01, 0x0D]`
- ⚠️ **10/21 passing** - discovered multiple bugs

### 3. Unified Test Runner (`run_all_tests.py`)
- Runs all tests with single command
- Generates timestamped test report files
- Includes date and MCR version in reports

### 4. Test Reports (auto-generated)
- **Format**: `test_results_YYYYMMDD_HHMMSS.txt`
- **Location**: `tests/` directory
- **Contents**: Full test results, failures, errors

## Running Tests

### Run Everything
```bash
cd tests
python run_all_tests.py
```

**Output**: Console summary + test report file

### Run Only Fuzz Tests
```bash
cd tests
python run_fuzz_tests.py
```

### Run Only Error Propagation Tests
```bash
python -m unittest test_error_handling -v
```

## Test Results Summary

### Current Status (2026-06-30)
- **Total Tests**: 46
- **Passing**: 36 (78%)
- **Failing**: 10 (22%)
- **MCR Version**: v.3.5.0
- **Runtime**: <1 second

### Fuzz Tests: ✅ 25/25 Passing
- Command overruns handled ✓
- Response overruns handled ✓
- Exceptions caught properly ✓
- Timeout logic works ✓

### Error Propagation: ⚠️ 10/21 Passing
- Found bugs in error handling
- Some functions don't propagate errors
- Error logging inconsistent

## Bugs Discovered

### 🔴 Critical: IndexError in readBoardSN()
**File**: [TheiaMCR.py:1322](../TheiaMCR/TheiaMCR.py#L1322)  
**Issue**: Crashes when accessing `response[-4]` on short error responses  
**Test**: `test_readBoardSN_error_response`

**Fix**:
```python
# Add length check before accessing array indices
if response == None or len(response) < 4:
    MCRControl.log.error("Error: Invalid response")
    return ''
```

### 🟡 Medium: readFWRevision() Returns Wrong Value
**File**: [TheiaMCR.py:~1290](../TheiaMCR/TheiaMCR.py#L1290)  
**Issue**: Returns `'1'` instead of `''` on error  
**Test**: `test_readFWRevision_error_response`

**Fix**: Validate response format before parsing

### 🟡 Medium: Motor Functions Don't Propagate Errors
**Issue**: `moveRel()`, `moveAbs()`, `home()` return success even when `_sendCmd()` fails  
**Tests**: `test_moveRel_error_response`, `test_moveAbs_error_response`, etc.

**Impact**: Application thinks move succeeded when it failed

### 🟡 Medium: Errors Not Logged
**Issue**: Failures don't always get logged to `err.finalError`  
**Test**: `test_error_codes_logged_to_finalError`

## What the Tests Tell You

### Fuzz Tests Answer:
- ✅ Does `_sendCmd()` crash with bad inputs? **No**
- ✅ Does it handle oversized commands/responses? **Yes**
- ✅ Does it catch serial port exceptions? **Yes**
- ✅ Does timeout logic work? **Yes**

### Error Propagation Tests Answer:
- ⚠️ Do functions handle `_sendCmd()` errors properly? **Sometimes**
- ❌ Are errors logged consistently? **No**
- ⚠️ Do functions return error codes correctly? **Sometimes**
- ⚠️ Is response validation complete? **No**

## Test Report Files

Each run creates a report in `tests/`:

```
test_results_20260630_144127.txt
```

**Contents**:
- Date, MCR version, Python version
- Test counts (pass/fail/error/skip)
- Detailed failure traces
- Execution time

## Interpreting Test Results

### Console Output
```
======================================================================
TheiaMCR Comprehensive Test Suite
======================================================================
Date: 2026-06-30 14:41:27
MCR Version: v.3.5.0
======================================================================

Found 46 tests across all test files

... (test execution) ...

======================================================================
TEST SUMMARY
======================================================================
Tests run: 46
Successes: 36
Failures: 9
Errors: 1
Time elapsed: 0.869 seconds

[FAIL] SOME TESTS FAILED
[FAIL] Test report saved to: test_results_20260630_144127.txt
```

### What Each Status Means

- **Success (36)**: Test passed - expected behavior confirmed
- **Failure (9)**: Test expected different behavior - may indicate bug
- **Error (1)**: Test couldn't complete - usually code issue
- **Skip (0)**: Test was skipped

## Next Steps

### 1. Review Bugs
Read [TEST_SUMMARY.md](TEST_SUMMARY.md) for detailed bug descriptions

### 2. Fix Critical Bugs
- IndexError in `readBoardSN()`
- Error parsing in `readFWRevision()`

### 3. Re-run Tests
```bash
cd tests
python run_all_tests.py
```

### 4. Check Progress
Compare new report file to previous ones to track improvements

### 5. Add to CI/CD
```yaml
# GitHub Actions example
- name: Run TheiaMCR tests
  run: |
    cd tests
    python run_all_tests.py
```

## Documentation Files

- **[TEST_SUMMARY.md](TEST_SUMMARY.md)** - Complete test analysis with bug details
- **[FUZZ_TEST_SUMMARY.md](FUZZ_TEST_SUMMARY.md)** - Fuzz testing documentation
- **[README_FUZZ_TESTS.md](README_FUZZ_TESTS.md)** - How to add/modify fuzz tests
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference
- **Test reports** - Auto-generated result files

## Adding Your Own Tests

### Add to Fuzz Tests
Edit `test_fuzz_sendCmd.py`:
```python
def test_my_new_scenario(self):
    """Test description"""
    # Setup mock
    type(self.mock_serial).in_waiting = PropertyMock(return_value=3)
    self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
    
    # Test
    cmd = bytearray([0x76, 0x0D])
    response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
    
    # Assert
    self.assertEqual(len(response), 3)
```

### Add to Error Propagation Tests
Edit `test_error_handling.py`:
```python
def test_my_error_case(self):
    """Test description"""
    # Mock error response
    with patch.object(self.mcr_instance.MCRBoard.com, '_sendCmd', 
                     return_value=bytearray([0x74, 0x01, 0x0D])):
        result = self.mcr_instance.focus.moveRel(100)
    
    # Check error handling
    self.assertNotEqual(result, err.ERR_OK)
```

## Tips

1. **Run tests after code changes** to catch regressions
2. **Save test reports** to track progress over time
3. **Fix critical bugs first** (crashes, incorrect returns)
4. **Use test failures as documentation** - they show expected vs actual behavior
5. **Add tests for bug fixes** to prevent recurrence

## Questions?

- Fuzz testing: See [FUZZ_TEST_SUMMARY.md](FUZZ_TEST_SUMMARY.md)
- Error testing: See [TEST_SUMMARY.md](TEST_SUMMARY.md)
- Commands: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- Test reports: Check `test_results_*.txt` files

---

**Created**: 2026-06-30  
**MCR Version**: v.3.5.0  
**Test Count**: 46 (25 fuzz + 21 error propagation)  
**Status**: Operational - discovering bugs as designed
