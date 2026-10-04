# TheiaMCR Testing - Quick Start Guide

### Verified passing checks
- Fuzz testing for `_sendCmd()` remains stable and passes across malformed inputs and oversized responses.
- Valid firmware-version parsing now passes for the expected board payload:
  - `[0x76, 0x05, 0x01, 0x02, 0x03, 0x04, 0x0D]`
  - expected result: `5.1.2.3.4`
- Valid serial-number parsing now passes for the expected board payload:
  - `[0x79, 0x05, 0x50, 0x00, 0x00, 0x80, 0x95, 0x0D]`
  - expected result: `055-008095`
- Short error responses are now handled without crashing in `readBoardSN()`.

### Remaining known issues
The broader error propagation suite still shows open failures in some motor-related code paths. These are tracked as follow-up fixes rather than regressions in the validated parsing behavior.

- `moveRel()` and `home()` can still return `ERR_OK` even when the board reports an error.
- `multiple_errors_accumulate` is still incomplete.
- The `_motorInit()` call signature mismatch remains under investigation.

## What the suite covers

### 1. Fuzz Tests (`test_fuzz_sendCmd.py`)
- Validates `_sendCmd()` under malformed command bytes, long payloads, weird timing, and exception paths.
- Confirms the command layer does not crash on bad data.
- ✅ Verified passing

### 2. Response Validation Tests (`test_error_handling.py`)
- Tests both invalid responses and valid firmware/SN payloads.
- Covers the HTTP-like board protocol patterns used by the controller.
- ✅ Valid FW/SN parsing passes
- ⚠️ Remaining motor error propagation failures still need attention

### 3. Unified Test Runner (`run_all_tests.py`)
- Runs the full suite from one entry point.
- Generates timestamped files with the current date, platform, Python version, and summary.
- Useful for tracking regressions over time.

## Running the tests

### Run the full suite
```bash
cd tests
python run_all_tests.py
```

### Run only the fuzz tests
```bash
cd tests
python -m unittest test_fuzz_sendCmd -v
```

### Run only the error-handling suite
```bash
cd tests
python -m unittest test_error_handling -v
```

### Run the specific valid-response checks
```bash
cd tests
python -m unittest \
  test_error_handling.TestErrorPropagation.test_readFWRevision_valid_response \
  test_error_handling.TestErrorPropagation.test_readBoardSN_valid_response -v
```

## Current known results

### Verified working as expected
- `_sendCmd()` robustness: pass
- Valid firmware-version parsing: pass
- Valid serial-number parsing: pass
- Short error-response handling in `readBoardSN()`: pass

### Still not fully green
- Full error propagation suite: partial failures remain
- Motor-level error propagation: still unreliable in some calls
- `_motorInit()` compatibility: still failing under current test assumptions

## Key bug fixes already verified

### `readBoardSN()` short-response guard
The code no longer crashes when the response is too short for the expected payload layout. It returns an empty value and logs the communication error instead of throwing an `IndexError`.

### Valid response parsing
The valid board payloads are now explicitly checked and match the expected outputs:
- Firmware version: `5.1.2.3.4`
- Serial number: `055-008095`

## Recommended next steps

1. Finish the remaining motor error-propagation fixes.
2. Reconcile `_motorInit()` with the actual function signature.
3. Re-run the full suite after each fix.
4. Keep the generated reports in `tests/` as the project’s regression record.

## Test report files

Each run creates a timestamped report under the `tests/` directory, including:
- date and time
- MCR version
- platform and Python version
- total tests, pass/fail counts
- failure and error traces

Example:
```text
test_results_20260630_152241.txt
```

## Documentation set

- [TEST_SUMMARY.md](TEST_SUMMARY.md)
- [FUZZ_TEST_SUMMARY.md](FUZZ_TEST_SUMMARY.md)
- [README_FUZZ_TESTS.md](README_FUZZ_TESTS.md)
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- [GETTING_STARTED.md](GETTING_STARTED.md)

## Notes for future contributors

When adding a new regression test, prefer one of these two patterns:

- Valid board response test: confirm the parser returns the exact expected value.
- Error response test: confirm the function returns an empty/failed result and logs the issue without crashing.

This gives a clear separation between parsing correctness and communication error handling, which is the core of the production behavior for this board interface.
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
