# Fuzz Testing for TheiaMCR._sendCmd

## Overview

This fuzz testing suite validates the robustness of the `_sendCmd` function in TheiaMCR.py against:
- Command overruns (commands that are too long or too short)
- Malformed responses from the board
- Response overruns (responses that are too long)
- Serial port exceptions and errors
- Timeout scenarios
- Edge cases and random data

## Test Categories

### 1. Command Overrun Tests
- **Extremely long commands** (1000 bytes)
- **Slightly oversized commands** (15 bytes vs typical 12)
- **Zero-length commands**
- **Single byte commands**
- **Commands without terminators**

### 2. Response Overrun Tests
- **Extremely long responses** (1000 bytes)
- **Oversized responses without terminators**
- **Zero-length responses**
- **Single byte responses**

### 3. Malformed Response Tests
- **Invalid start bytes**
- **All zeros responses**
- **All 0xFF responses**
- **Random byte sequences**
- **Responses with embedded terminators**

### 4. Timing and Timeout Tests
- **Response timeouts** (no data received)
- **Delayed responses** (data arrives after initial wait)

### 5. Serial Port Exception Tests
- **Write failures**
- **Read failures**
- **Readline failures**
- **AttributeError** (uninitialized serial port)

### 6. Random Fuzz Tests
- **100 commands with random lengths** (0-500 bytes)
- **100 responses with random lengths** (0-500 bytes)
- **Random byte content**

## Running the Tests

### Method 1: Run directly with Python

```bash
cd tests
python test_fuzz_sendCmd.py
```

### Method 2: Run with unittest discovery

```bash
# From project root
python -m unittest discover -s tests -p "test_fuzz*.py" -v
```

### Method 3: Run specific test class

```bash
python -m unittest tests.test_fuzz_sendCmd.TestSendCmdFuzz -v
```

### Method 4: Run specific test

```bash
python -m unittest tests.test_fuzz_sendCmd.TestSendCmdFuzz.test_command_extremely_long -v
```

## Expected Results

All tests should **PASS**. The `_sendCmd` function should:
1. Handle any command length gracefully
2. Accept any response length without crashing
3. Return appropriate error responses on serial exceptions
4. Set `boardCommunicationState` correctly based on success/failure
5. Never crash or raise unhandled exceptions

## Test Output Format

```
test_command_extremely_long (__main__.TestSendCmdFuzz)
Test sending extremely long command (1000 bytes) ... ok
test_command_no_terminator (__main__.TestSendCmdFuzz)
Test command without proper 0x0D terminator ... ok
...

----------------------------------------------------------------------
Ran 30 tests in 0.123s

OK
```

## Interpreting Failures

If a test fails:

1. **Check the error message** - It will indicate what assertion failed
2. **Review the test case** - Understand what scenario was being tested
3. **Check _sendCmd implementation** - Look for missing bounds checks or error handling
4. **Add protective code** - Add validation or error handling as needed

### Common failure scenarios to fix:

- **IndexError**: Missing bounds check on response/command buffers
- **TypeError**: Incorrect type handling (e.g., None instead of bytearray)
- **Infinite loop**: Timeout logic not working correctly
- **Unhandled exception**: Missing try/except for serial operations

## Adding More Tests

To add additional fuzz tests:

1. Add a new test method to `TestSendCmdFuzz` class
2. Follow naming convention: `test_<descriptive_name>`
3. Set up mock serial port behavior
4. Call `_sendCmd` with fuzz input
5. Assert expected behavior

Example:
```python
def test_my_new_scenario(self):
    \"\"\"Test description\"\"\"
    # Setup
    self.mock_serial.in_waiting = PropertyMock(return_value=3)
    self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
    
    # Execute
    cmd = bytearray([0x76, 0x0D])
    response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
    
    # Assert
    self.assertEqual(len(response), 3)
```

## Dependencies

- Python 3.7+
- unittest (standard library)
- unittest.mock (standard library)
- pyserial (for Serial spec)
- TheiaMCR module

## Integration with CI/CD

To integrate with continuous integration:

```yaml
# Example GitHub Actions workflow
- name: Run fuzz tests
  run: |
    python -m unittest discover -s tests -p "test_fuzz*.py" -v
```

## Performance

The full test suite runs in under 5 seconds on typical hardware. Random fuzz tests are limited to 100 iterations per test to balance coverage with speed.

## Notes

- Tests use mocked serial ports, so no physical hardware is required
- Tests are isolated - each test sets up and tears down its own MCRControl instance
- `boardCommunicationState` is verified to ensure proper error flagging
- Tests cover both expected error handling and unexpected edge cases
