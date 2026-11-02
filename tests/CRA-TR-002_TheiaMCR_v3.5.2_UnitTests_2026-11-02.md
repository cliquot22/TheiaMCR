# TheiaMCR Test Report

## ✅ ALL TESTS PASSED

## 📊 Executive Summary

- **Report Name**: `CRA-TR-002_TheiaMCR_v3.5.2_UnitTests_2026-11-02.md`
- **Date**: 2026-11-02 12:01:57
- **Product**: TheiaMCR
- **Revision**: TR-002
- **MCR Version**: v.3.5.2
- **Platform**: win32
- **Total Tests**: 99
- **Passed**: 99 ✅
- **Failed**: 0 ❌
- **Errors**: 0 ⚠️
- **Skipped**: 0 ⏭️
- **Pass Rate**: 100.0%
- **Runtime**: 59.161 seconds

## 🧪 Tests Executed

The following test functions were executed in this run:

- `test_error_handling.TestErrorPropagation.test_empty_error_response`
- `test_error_handling.TestErrorPropagation.test_error_codes_logged_to_finalError`
- `test_error_handling.TestErrorPropagation.test_error_response_sets_communication_state_false`
- `test_error_handling.TestErrorPropagation.test_home_error_response`
- `test_error_handling.TestErrorPropagation.test_motorInit_error_response`
- `test_error_handling.TestErrorPropagation.test_motorMoveTo_error_response`
- `test_error_handling.TestErrorPropagation.test_motor_position_unchanged_on_error`
- `test_error_handling.TestErrorPropagation.test_moveAbs_error_response`
- `test_error_handling.TestErrorPropagation.test_moveRel_error_response`
- `test_error_handling.TestErrorPropagation.test_multiple_errors_accumulate`
- `test_error_handling.TestErrorPropagation.test_multiple_motor_failures`
- `test_error_handling.TestErrorPropagation.test_readBoardSN_error_response`
- `test_error_handling.TestErrorPropagation.test_readBoardSN_none_response`
- `test_error_handling.TestErrorPropagation.test_readBoardSN_valid_response`
- `test_error_handling.TestErrorPropagation.test_readFWRevision_error_response`
- `test_error_handling.TestErrorPropagation.test_readFWRevision_none_response`
- `test_error_handling.TestErrorPropagation.test_readFWRevision_valid_response`
- `test_error_handling.TestErrorPropagation.test_readMotorSetup_error_response`
- `test_error_handling.TestErrorPropagation.test_short_error_response`
- `test_error_handling.TestErrorPropagation.test_timeout_response_handled`
- `test_error_handling.TestErrorPropagation.test_writeMotorSetup_error_response`
- `test_error_handling.TestSerialPortFailure.test_communication_recovery_attempt`
- `test_error_handling.TestSerialPortFailure.test_serial_exception_during_operation`
- `test_error_handling.TestSerialPortFailure.test_serial_exception_while_waiting_for_reply`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_attribute_error`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_command_extremely_long`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_command_no_terminator`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_command_one_byte`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_command_slightly_oversized`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_command_zero_length`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_multiple_rapid_commands`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_all_0xFF`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_all_zeros`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_delayed`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_extremely_long`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_invalid_start_byte`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_one_byte`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_oversized_no_terminator`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_random_bytes`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_timeout`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_with_embedded_terminators`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_response_zero_length`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_serial_exception_on_read`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_serial_exception_on_readline`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_serial_exception_on_write`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_serial_port_string_instead_of_object`
- `test_fuzz_sendCmd.TestSendCmdFuzz.test_special_command_set_comm_path`
- `test_fuzz_sendCmd.TestSendCmdRandomFuzz.test_random_command_lengths`
- `test_fuzz_sendCmd.TestSendCmdRandomFuzz.test_random_response_lengths`
- `test_input_validation.TestBoardSetupValidation.test_setCommunicationPath_accepts_valid_path`
- `test_input_validation.TestBoardSetupValidation.test_setCommunicationPath_rejects_invalid_path`
- `test_input_validation.TestBoardSetupValidation.test_writeMotorSetup_accepts_valid_values`
- `test_input_validation.TestBoardSetupValidation.test_writeMotorSetup_rejects_invalid_values`
- `test_input_validation.TestMotorInitValidation.test_failed_init_keeps_existing_motor`
- `test_input_validation.TestMotorInitValidation.test_focusInit_rejects_invalid_accel`
- `test_input_validation.TestMotorInitValidation.test_focusInit_rejects_invalid_move`
- `test_input_validation.TestMotorInitValidation.test_focusInit_rejects_invalid_pi`
- `test_input_validation.TestMotorInitValidation.test_focusInit_rejects_invalid_steps`
- `test_input_validation.TestMotorInitValidation.test_init_accepts_min_and_max`
- `test_input_validation.TestMotorInitValidation.test_irisInit_rejects_invalid_steps_and_move`
- `test_input_validation.TestMotorInitValidation.test_zoomInit_rejects_invalid_steps_and_pi`
- `test_input_validation.TestMoveValidation.test_moveAbs_accepts_min_and_max`
- `test_input_validation.TestMoveValidation.test_moveAbs_limits_step_above_max`
- `test_input_validation.TestMoveValidation.test_moveAbs_rejects_invalid_step`
- `test_input_validation.TestMoveValidation.test_moveAbs_rounds_float_step`
- `test_input_validation.TestMoveValidation.test_moveRel_accepts_valid_steps`
- `test_input_validation.TestMoveValidation.test_moveRel_rejects_invalid_correctForBL`
- `test_input_validation.TestMoveValidation.test_moveRel_rejects_invalid_steps`
- `test_input_validation.TestMoveValidation.test_moveRel_rejects_steps_too_large_with_limits_off`
- `test_input_validation.TestMoveValidation.test_unsupported_motor_functions`
- `test_input_validation.TestSpeedValidation.test_invalid_homingSpeed_at_init_uses_default`
- `test_input_validation.TestSpeedValidation.test_setHomingSpeed_range`
- `test_input_validation.TestSpeedValidation.test_setMotorSpeed_focus_range`
- `test_input_validation.TestSpeedValidation.test_setMotorSpeed_iris_range`
- `test_input_validation.TestStateValidation.test_IRC_state_range`
- `test_input_validation.TestStateValidation.test_setRespectLimits_iris_not_supported`
- `test_input_validation.TestStateValidation.test_setRespectLimits_rejects_invalid_state`
- `test_no_unintended_motion.TestDeviceIdentification.test_invalid_reply_is_not_initialized`
- `test_no_unintended_motion.TestDeviceIdentification.test_no_commands_after_failed_identification`
- `test_no_unintended_motion.TestDeviceIdentification.test_valid_reply_initializes`
- `test_no_unintended_motion.TestNoMotionOnErrors.test_failed_move_keeps_step_position`
- `test_no_unintended_motion.TestNoMotionOnErrors.test_invalid_motor_init_parameters_send_no_motion`
- `test_no_unintended_motion.TestNoMotionOnErrors.test_invalid_move_parameters_send_no_motion`
- `test_no_unintended_motion.TestNoMotionOnErrors.test_no_board_reply_sends_no_motion`
- `test_no_unintended_motion.TestNoMotionOnErrors.test_wrong_device_reply_sends_no_motion`
- `test_no_unintended_motion.TestNoMotionOnStartup.test_MCRControl_creation_sends_only_firmware_request`
- `test_no_unintended_motion.TestNoMotionOnStartup.test_close_sends_no_motion`
- `test_no_unintended_motion.TestNoMotionOnStartup.test_homing_only_when_requested`
- `test_no_unintended_motion.TestNoMotionOnStartup.test_import_opens_no_serial_port`
- `test_no_unintended_motion.TestNoMotionOnStartup.test_motor_init_without_homing_sends_no_motion`
- `test_robustness.TestBoardNotResponding.test_error_reply_returns_error`
- `test_robustness.TestBoardNotResponding.test_no_reply_times_out_with_error`
- `test_robustness.TestDisconnect.test_home_after_reconnect`
- `test_robustness.TestDisconnect.test_unplug_between_commands`
- `test_robustness.TestDisconnect.test_unplug_during_command`
- `test_robustness.TestRepeatedCalls.test_no_memory_growth_on_repeated_errors`
- `test_robustness.TestRepeatedCalls.test_no_memory_growth_on_repeated_moves`
- `test_robustness.TestRepeatedCalls.test_rapid_repeated_board_queries`
- `test_robustness.TestRepeatedCalls.test_rapid_repeated_moves`

## ✅ No Bugs Detected

All tests passing! The code is working as expected.

## 📋 Test Details

### Test Categories

| Category | Status | Count |
|----------|--------|-------|
| Fuzz Tests | ✅ | 0 failed |
| Error Handling | ✅ | 0 failed |

## 🎉 Success!

All tests are passing. Consider:
1. Adding more edge case tests
2. Increasing test coverage
3. Adding integration tests

---

**Report Generated**: 2026-11-02 12:01:57

**MCR Version**: v.3.5.2

**Test Command**: `python run_all_tests.py`
