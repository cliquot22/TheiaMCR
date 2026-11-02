# TheiaMCR Unit Tests — Running the Full Suite

This file covers the full unit test suite: how to run it, where the results go, what to check when a test fails,
and how to keep the CRA documents up to date after a run.

For the `_sendCmd()` fuzz tests only, see:
- [README_FUZZ_TESTS.md](README_FUZZ_TESTS.md) — what the fuzz tests cover and how to interpret them
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) — commands for running individual fuzz tests

## Requirements

- Python 3.10 or newer
- pyserial (`pip install pyserial`)
- No MCR board is needed.  All tests replace the serial port with a simulated board, so the results are the same
  whether or not a board is connected.

## Running the tests

### Full suite (use this for CRA evidence)
From the project root:
```bash
python tests/run_all_tests.py
```
The runner finds every `test_*.py` file in `tests/`, runs it, prints a summary, and writes the report file
(see [Where to find the results](#where-to-find-the-results)).  It always tests the TheiaMCR code in this
repository, even if a different TheiaMCR version is installed with pip.  It returns exit code 0 if all tests
pass and 1 if any fail.

### One test file
```bash
cd tests
python -m unittest test_input_validation -v
```

### One test
```bash
cd tests
python -m unittest test_robustness.TestDisconnect.test_unplug_during_command -v
```

### CRA report script test
The test for the GitHub CRA report script is not part of this suite.  It tests the release tooling, not the
module.  Run it after changing `.github/scripts/generate_cra_report.py`:
```bash
python .github/tests/test_cra_report_script.py
```

## What the suite covers

| File | Tests | What it checks | CRA-RA-002 test |
|------|-------|----------------|-----------------|
| `test_fuzz_sendCmd.py` | 25 | `_sendCmd()` with malformed, oversized, empty and random commands and replies; serial port exceptions; timeouts | PY-03 |
| `test_error_handling.py` | 24 | Error replies from the board are passed up correctly; valid firmware/serial number parsing; serial exceptions during a move | PY-03, PY-10 |
| `test_input_validation.py` | 28 | Every public function called with min, max, out-of-range, NaN, infinity, None, string and bool arguments; invalid values return the documented error and nothing is sent to the board | PY-01, PY-02 |
| `test_no_unintended_motion.py` | 13 | No motor move command on import, on `MCRControl()` creation, on motor init without homing, on `close()`, or on error paths; only the firmware-version request is sent before the board is identified; no reply, a different device, a wrong-format reply or firmware older than 5 leaves the module not initialized without an exception, and nothing more is sent | PY-11, PY-16 (cases a and b) |
| `test_robustness.py` | 9 | Rapid repeated calls, memory growth, board not replying, USB cable unplugged between and during commands, recovery after reconnect | PY-10 |

`mock_mcr_board.py` is not a test file.  It is the simulated board used by the newer tests: it replies to each
command at the byte level, records every command written, and can simulate an unplugged cable.  Because the
real module code runs against it, a change to the board protocol or to `readFWRevision()` may need a matching
change in `mock_mcr_board.py`.

Not covered by this suite (evidence comes from elsewhere):
- PY-04 to PY-07 (static analysis, dependency scan, SBOM, secret scan): the GitHub release workflow, see
  [Next steps](#next-steps-after-a-test-run).
- PY-08, PY-09, PY-12, PY-13, PY-15: manual review.
- PY-16 case (c), a reassigned or renamed port: manual test with a real board.
- PY-14: not applicable (the module loads no calibration or configuration files).
- Multi-threaded use: the module is not thread-safe (see the main README), so this is not tested.

## Where to find the results

1. **Console:** each test is listed with `ok`, `FAIL` or `ERROR`, followed by a summary and the full traceback
   of every failure.
2. **Report file:** written to the `tests/` folder as
   ```
   CRA-TR-002_TheiaMCR_<version>_UnitTests_<date>.md
   ```
   for example `CRA-TR-002_TheiaMCR_v3.5.2_UnitTests_2026-10-07.md`.
   - `<version>` comes from `MCR_REVISION` in `TheiaMCR/TheiaMCR.py`.  Update it before the final run for a
     release, or the report will carry the old version number.
   - `<date>` is the run date only, so running the suite again on the same day overwrites that day's report.
   - The report lists the platform, test counts, pass rate, every test that ran, and the traceback of every
     failure.
   - The "Bugs Discovered" section is generated automatically by matching keywords in the failure messages.
     Treat it as a starting point; check each failure yourself.

## If a test fails

Work through these in order:

1. **Every test, or every test in one file, fails in `setUp`.**  Usually a setup problem, not a module bug.
   - `ModuleNotFoundError: No module named 'TheiaMCR'` or `serial`: run from the project root with
     `python tests/run_all_tests.py`, and check that pyserial is installed.
   - The MCR version printed at the top of the run is not the one you are working on: you are testing a
     different copy of the module.
   - `MCRControl()` no longer initializes against the simulated board: `readFWRevision()` or the initialization
     code changed.  Check that `FW_REVISION_REPLY` in `mock_mcr_board.py` still matches what the module
     expects from a real board.

2. **`ERROR` (an exception was raised).**  The module crashed on an input or board reply it should have
   handled.  For the CRA, a crash is the most serious type of result: fix the module, not the test.

3. **`FAIL` (an assertion did not hold).**  Decide whether the module's behavior changed on purpose:
   - **Not on purpose:** it is a regression.  Fix the module.
   - **On purpose** (for example a new speed range or a new parameter limit): update the test to the new
     behavior, record the change in `history.txt`, and update the main README if the public behavior changed.
   - Never change a test only to make it pass.  The test is the evidence that the requirement is met.

4. **Timing or memory tests in `test_robustness.py`.**
   - A call took longer than `MAX_CALL_TIME`: check for a new wait or retry loop that has no time limit.  On a
     very slow or busy computer, run the test again before investigating.
   - Memory grew more than `MAX_MEMORY_GROWTH`: check for a list or cache that is added to on every call and
     never cleared.  If you added a `patch(...)` with `return_value` around a repeated call, the Mock itself
     records every call and grows; use a plain function instead.

5. **A new public function has no tests.**  Add it to `test_input_validation.py` (every argument, invalid and
   min/max values).  If it can move a motor, also add it to `test_no_unintended_motion.py`.

After a fix, run the whole suite again, not only the failing test.

## Next steps after a test run

Do these for each release.  Steps 1–7 are in this repository and on GitHub/PyPI; steps 8–9 are in the CRA
technical file.

### Before the release
1. **Version numbers:** update `MCR_REVISION` in `TheiaMCR/TheiaMCR.py` and `version` in `pyproject.toml`.
2. **History:** add the changes to `history.txt`, including any change in test results or new tests.
3. **Final test run:** run `python tests/run_all_tests.py`.  All tests should pass.  If a failure is
   accepted for this release, record why in the CRA risk assessment (step 8).
4. **Push the code:** commit the changes and push everything to `main`.  The test report is not committed:
   `tests/CRA-TR-*.md` is in `.gitignore` because the repository is public.  The report is attached to the
   GitHub release in step 5 and archived in the CRA technical file in step 9.  Keep the older reports in the
   evidence folder; they are the regression history.

### Publishing the GitHub release
5. **Create the release** from the pushed `main` commit, on GitHub or with the GitHub CLI:
   - **GitHub:** *Releases* → *Draft a new release* → *Choose a tag*, type the new tag (e.g. `v3.5.2`, no dot
     after the `v`, matching the earlier tags) and create it on publish, target `main` → title (e.g.
     `v3.5.2`) → paste this version's lines from `history.txt` as the release notes → drag the unit test
     report from step 3 into *Attach binaries* → *Publish release*.
   - **GitHub CLI** (the report file is attached to the release):
     ```bash
     gh release create v3.5.2 tests/CRA-TR-002_TheiaMCR_v3.5.2_UnitTests_<date>.md --target main --title "v3.5.2" --notes "<this version's lines from history.txt>"
     ```
   Attach only an all-pass report: the release is public.
   A saved draft does not start the CRA workflow; it runs only when the release is published.
6. **Upload to PyPI** from the same commit:
   ```bash
   py -m pip install --upgrade build twine
   py -m build
   twine upload dist/theiamcr-3.5.2*
   ```
   Upload only the new version's files: `dist/` keeps the files from earlier builds, and `twine upload dist/*`
   would try to upload them again.  To try the package first, upload to TestPyPI with
   `twine upload --repository testpypi dist/theiamcr-3.5.2*` and install it with
   `pip install --index-url https://test.pypi.org/simple/ --no-deps --upgrade TheiaMCR`.
7. **Check the release workflow:** the `cra-security-report` workflow (GitHub *Actions* tab) runs automatically
   when the release is published.  When it finishes, check on the release page that `cra-evidence-report.html`
   and the SBOM JSON file are attached.  If the report status is `REVIEW REQUIRED`, review the open
   code-scanning, Dependabot or secret-scanning alerts it lists before signing off.  If the workflow failed or
   the files are missing, run it again from the *Actions* tab (*Run workflow*, with the release tag).

### Updating the CRA documents
8. **Update the risk assessment (CRA-RA-002):**
   - **Section 3, test catalog:** fill in Result, Version & Date Tested, and Evidence Reference.
     - PY-01, PY-02, PY-03, PY-10, PY-11: the unit test report from step 3 (attached to the GitHub release).
     - PY-16: the unit test report from step 3 for cases (a) and (b), plus the manual test record for case (c).
     - PY-04, PY-05, PY-07: `cra-evidence-report.html` on the GitHub release (include the Actions run number).
     - PY-06: the SBOM JSON file on the GitHub release and the CRA SBOM document.
     - Manual review items (PY-08, PY-09, PY-12, PY-13, PY-15): record who reviewed what, on which
       version, and the result.
   - **Section 4, risk register:** if a test result or a fix changes the likelihood, impact or mitigation of a
     risk, update its row and the residual risk.
   - **Section 5, findings summary:** update the counts and the outstanding items.
9. **Archive the evidence:** copy the unit test report, `cra-evidence-report.html` and the SBOM file into the CRA
   technical file evidence folder, so the evidence references in CRA-RA-002 point to files that exist there.

### When tests are added or changed
- Name new test files `test_*.py` so `run_all_tests.py` finds them.
- Add the file to the table in [What the suite covers](#what-the-suite-covers) with its CRA test ID.
- If the new tests change which CRA tests have evidence, update the Section 3 rows in CRA-RA-002 at the next
  release.
