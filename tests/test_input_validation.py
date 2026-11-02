"""
PY-02 input validation tests for the TheiaMCR public functions (CRA-RA-002).
Each public function is called with min, max, out-of-range, wrong-type, NaN, infinity, None and bool arguments.
Invalid values must return the documented error value without raising an exception and without writing
any bytes to the serial port.  Valid min/max values must be accepted and sent to the board.
"""

import math
import unittest

from mock_mcr_board import createMCR, closeMCR
import TheiaMCR as mcr
import TheiaMCR.errList as err

# values that are never a valid number for any parameter
NOT_A_NUMBER = [math.nan, math.inf, -math.inf, None, 'abc', '100', [], {}, True, False]
# values that are never a valid True/False parameter
NOT_A_BOOL = [None, 'abc', 'False', 2, -1, 0.5, math.nan, []]

FOCUS_STEPS, FOCUS_PI = 8390, 7959
FZ_MIN, FZ_MAX = mcr.TheiaMCR.MCR_FZ_MIN_SPEED, mcr.TheiaMCR.MCR_FZ_MAX_SPEED
IRIS_MIN, IRIS_MAX = mcr.TheiaMCR.MCR_IRIS_MIN_SPEED, mcr.TheiaMCR.MCR_IRIS_MAX_SPEED
IRIS_STEPS = 75


class _MCRTestCase(unittest.TestCase):
    def setUp(self):
        self.MCR, self.board = createMCR()
        self.assertTrue(self.MCR.boardInitialized, 'fake board did not initialize')
        self.MCR.focusInit(FOCUS_STEPS, FOCUS_PI, move=False)
        self.MCR.zoomInit(3227, 3119, move=False)
        self.MCR.irisInit(IRIS_STEPS, move=False)
        self.MCR.IRCInit()
        self.board.clear()
        err.clearErrorList()

    def tearDown(self):
        closeMCR(self.MCR)

    def assertRejected(self, func, value, expected, *args):
        """Call func with the value and check the documented error is returned and nothing is sent to the board."""
        self.board.clear()
        with self.subTest(func=func.__name__, value=value):
            try:
                result = func(*args, value) if args else func(value)
            except Exception as e:
                self.fail(f'{func.__name__}({value!r}) raised {type(e).__name__}: {e}')
            self.assertEqual(result, expected, f'{func.__name__}({value!r}) returned {result!r}')
            self.assertEqual(self.board.written, [], f'{func.__name__}({value!r}) wrote to the serial port')

    def assertSent(self, func, *args, **kwargs):
        """Call func with valid arguments and check a command was sent to the board."""
        self.board.clear()
        result = func(*args, **kwargs)
        self.assertNotEqual(self.board.written, [], f'{func.__name__}{args} did not send a command')
        return result


class TestMotorInitValidation(_MCRTestCase):
    def test_focusInit_rejects_invalid_steps(self):
        for value in NOT_A_NUMBER + [0, -1, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE + 1]:
            self.assertRejected(lambda v: self.MCR.focusInit(v, 100, move=False), value, False)

    def test_focusInit_rejects_invalid_pi(self):
        for value in NOT_A_NUMBER + [-1, FOCUS_STEPS + 1]:
            self.assertRejected(lambda v: self.MCR.focusInit(FOCUS_STEPS, v, move=False), value, False)

    def test_focusInit_rejects_invalid_move(self):
        for value in NOT_A_BOOL:
            self.assertRejected(lambda v: self.MCR.focusInit(FOCUS_STEPS, FOCUS_PI, move=v), value, False)

    def test_focusInit_rejects_invalid_accel(self):
        for value in NOT_A_NUMBER + [-1]:
            self.assertRejected(lambda v: self.MCR.focusInit(FOCUS_STEPS, FOCUS_PI, move=False, accel=v), value, False)

    def test_zoomInit_rejects_invalid_steps_and_pi(self):
        for value in NOT_A_NUMBER + [0, -1]:
            self.assertRejected(lambda v: self.MCR.zoomInit(v, 100, move=False), value, False)
        for value in NOT_A_NUMBER + [-1, 3228]:
            self.assertRejected(lambda v: self.MCR.zoomInit(3227, v, move=False), value, False)

    def test_irisInit_rejects_invalid_steps_and_move(self):
        for value in NOT_A_NUMBER + [-1, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE + 1]:
            self.assertRejected(lambda v: self.MCR.irisInit(v, move=False), value, False)
        for value in NOT_A_BOOL:
            self.assertRejected(lambda v: self.MCR.irisInit(IRIS_STEPS, move=v), value, False)

    def test_failed_init_keeps_existing_motor(self):
        motor = self.MCR.focus
        self.MCR.focusInit(math.nan, FOCUS_PI, move=False)
        self.assertIs(self.MCR.focus, motor)

    def test_init_accepts_min_and_max(self):
        self.assertTrue(self.assertSent(self.MCR.focusInit, 1, 0, move=False))
        self.assertTrue(self.assertSent(self.MCR.focusInit, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE, move=False))
        self.assertTrue(self.assertSent(self.MCR.irisInit, 1, move=False))


class TestMoveValidation(_MCRTestCase):
    def test_moveAbs_rejects_invalid_step(self):
        for value in NOT_A_NUMBER + [-1, -1000]:
            self.assertRejected(self.MCR.focus.moveAbs, value, err.ERR_RANGE)
            self.assertRejected(self.MCR.iris.moveAbs, value, err.ERR_RANGE)
        self.assertEqual(self.MCR.focus.currentStep, 0)

    def test_moveAbs_accepts_min_and_max(self):
        self.assertEqual(self.assertSent(self.MCR.focus.moveAbs, 0), err.ERR_OK)
        self.assertEqual(self.assertSent(self.MCR.focus.moveAbs, FOCUS_STEPS), err.ERR_OK)

    def test_moveAbs_limits_step_above_max(self):
        self.assertEqual(self.assertSent(self.MCR.focus.moveAbs, FOCUS_STEPS + 1000), err.ERR_OK)
        self.assertEqual(self.MCR.focus.currentStep, FOCUS_STEPS)

    def test_moveAbs_rounds_float_step(self):
        self.assertEqual(self.assertSent(self.MCR.focus.moveAbs, 100.6), err.ERR_OK)
        self.assertEqual(self.MCR.focus.currentStep, 101)
        self.assertIsInstance(self.MCR.focus.currentStep, int)

    def test_moveRel_rejects_invalid_steps(self):
        tooLarge = mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE - mcr.TheiaMCR.MCR_BACKLASH_OVERSHOOT + 1
        for value in NOT_A_NUMBER + [tooLarge, -tooLarge]:
            self.assertRejected(self.MCR.focus.moveRel, value, err.ERR_RANGE)
            self.assertRejected(self.MCR.iris.moveRel, value, err.ERR_RANGE)
        self.assertEqual(self.MCR.focus.currentStep, 0)

    def test_moveRel_rejects_steps_too_large_with_limits_off(self):
        # with the PI limit off the steps are not limited by the module so they must still fit in the board command
        self.MCR.focus.setRespectLimits(False)
        self.assertRejected(self.MCR.focus.moveRel, 100000, err.ERR_RANGE)
        self.assertRejected(self.MCR.focus.moveRel, -100000, err.ERR_RANGE)

    def test_moveRel_rejects_invalid_correctForBL(self):
        for value in NOT_A_BOOL:
            self.assertRejected(lambda v: self.MCR.focus.moveRel(100, correctForBL=v), value, err.ERR_RANGE)

    def test_moveRel_accepts_valid_steps(self):
        self.assertEqual(self.assertSent(self.MCR.focus.moveRel, 100), err.ERR_OK)
        self.assertEqual(self.assertSent(self.MCR.focus.moveRel, -100), err.ERR_OK)

    def test_unsupported_motor_functions(self):
        self.assertRejected(self.MCR.IRC.moveAbs, 10, err.ERR_NOT_SUPPORTED)
        self.assertRejected(self.MCR.IRC.moveRel, 10, err.ERR_NOT_SUPPORTED)
        self.assertRejected(self.MCR.focus.state, 1, err.ERR_NOT_SUPPORTED)


class TestSpeedValidation(_MCRTestCase):
    def test_setMotorSpeed_focus_range(self):
        speed = self.MCR.focus.currentSpeed
        for value in NOT_A_NUMBER + [FZ_MIN - 1, FZ_MAX + 1, -100]:
            self.assertRejected(self.MCR.focus.setMotorSpeed, value, err.ERR_RANGE)
        self.assertEqual(self.MCR.focus.currentSpeed, speed)
        for value in (FZ_MIN, FZ_MAX):
            self.assertEqual(self.MCR.focus.setMotorSpeed(value), err.ERR_OK)
            self.assertEqual(self.MCR.focus.currentSpeed, value)

    def test_setMotorSpeed_iris_range(self):
        for value in NOT_A_NUMBER + [IRIS_MIN - 1, IRIS_MAX + 1]:
            self.assertRejected(self.MCR.iris.setMotorSpeed, value, err.ERR_RANGE)
        for value in (IRIS_MIN, IRIS_MAX):
            self.assertEqual(self.MCR.iris.setMotorSpeed(value), err.ERR_OK)

    def test_setHomingSpeed_range(self):
        speed = self.MCR.zoom.homingSpeed
        for value in NOT_A_NUMBER + [FZ_MIN - 1, FZ_MAX + 1]:
            self.assertRejected(self.MCR.zoom.setHomingSpeed, value, err.ERR_RANGE)
        self.assertEqual(self.MCR.zoom.homingSpeed, speed)
        for value in (FZ_MIN, FZ_MAX):
            self.assertEqual(self.MCR.zoom.setHomingSpeed(value), err.ERR_OK)
        for value in NOT_A_NUMBER + [IRIS_MIN - 1, IRIS_MAX + 1]:
            self.assertRejected(self.MCR.iris.setHomingSpeed, value, err.ERR_RANGE)

    def test_invalid_homingSpeed_at_init_uses_default(self):
        for value in (math.nan, None, 'abc'):
            with self.subTest(value=value):
                self.assertTrue(self.MCR.focusInit(FOCUS_STEPS, FOCUS_PI, move=False, homingSpeed=value))
                self.assertEqual(self.MCR.focus.homingSpeed, mcr.TheiaMCR.MCR_FZ_HOME_SPEED)


class TestStateValidation(_MCRTestCase):
    def test_IRC_state_range(self):
        for value in NOT_A_NUMBER + [0, 3, -1]:
            self.assertRejected(self.MCR.IRC.state, value, err.ERR_RANGE)
        for value in (1, 2):
            self.assertEqual(self.assertSent(self.MCR.IRC.state, value), value)

    def test_setRespectLimits_rejects_invalid_state(self):
        for value in NOT_A_BOOL:
            self.assertRejected(self.MCR.focus.setRespectLimits, value, True)
        self.assertTrue(self.MCR.focus.respectLimits)
        self.assertFalse(self.assertSent(self.MCR.focus.setRespectLimits, False))
        self.assertTrue(self.assertSent(self.MCR.focus.setRespectLimits, True))

    def test_setRespectLimits_iris_not_supported(self):
        self.assertRejected(self.MCR.iris.setRespectLimits, True, None)


class TestBoardSetupValidation(_MCRTestCase):
    def test_writeMotorSetup_rejects_invalid_values(self):
        valid = [True, False, FOCUS_STEPS, 100, 1500]
        invalid = {
            0: NOT_A_BOOL,
            1: NOT_A_BOOL,
            2: NOT_A_NUMBER + [0, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE + 1],
            3: NOT_A_NUMBER + [0, -1, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE + 1],
            4: NOT_A_NUMBER + [0, -1, mcr.TheiaMCR.MCR_MAX_COMMAND_VALUE + 1],
        }
        for index, values in invalid.items():
            for value in values:
                args = list(valid)
                args[index] = value
                self.board.clear()
                with self.subTest(parameter=index, value=value):
                    self.assertFalse(self.MCR.focus.writeMotorSetup(*args))
                    self.assertEqual(self.board.written, [])

    def test_writeMotorSetup_accepts_valid_values(self):
        self.assertTrue(self.assertSent(self.MCR.focus.writeMotorSetup, True, False, FOCUS_STEPS, FZ_MIN, FZ_MAX))
        self.assertEqual(self.board.written[-1][5:7], FOCUS_STEPS.to_bytes(2, 'big'))

    def test_setCommunicationPath_rejects_invalid_path(self):
        for value in NOT_A_NUMBER + [-1, 3, 255, 'serial', 'Usb']:
            self.assertRejected(self.MCR.MCRBoard.setCommunicationPath, value, False)

    def test_setCommunicationPath_accepts_valid_path(self):
        for value, expected in ((0, 0), (2, 2), ('USB', 1), ('i2c', 0)):
            with self.subTest(value=value):
                self.assertTrue(self.assertSent(self.MCR.MCRBoard.setCommunicationPath, value))
                self.assertEqual(self.board.written[-1], bytes([0x6B, expected, 0x0D]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
