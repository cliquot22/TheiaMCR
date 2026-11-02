"""
PY-11 unintended actuation / safe-state tests for TheiaMCR (CRA-RA-002).
No motor move command (0x62, 0x66, 0x73) may be sent on import, on MCRControl creation, during motor initialization
without homing, on close, or on error paths.  Homing only happens when it is requested explicitly (move=True).

PY-16 device identification tests (cases a and b): the firmware-version request is the only data sent until a
reply in the known format is received, and any other reply leaves the module not initialized without an exception.
"""

import math
import os
import subprocess
import sys
import unittest

from mock_mcr_board import FakeMCRBoard, createMCR, closeMCR, FW_REVISION_CMD
import TheiaMCR.errList as err

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# run in a separate Python process so the import is the first import of TheiaMCR
IMPORT_CHECK = r'''
import sys
from unittest.mock import patch
import serial
opened = []
with patch.object(serial, 'Serial', side_effect=lambda *a, **k: opened.append((a, k))):
    import TheiaMCR
print(len(opened))
'''


class TestNoMotionOnStartup(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)

    def test_import_opens_no_serial_port(self):
        run = subprocess.run([sys.executable, '-c', IMPORT_CHECK], cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), '0', 'importing TheiaMCR opened a serial port')

    def test_MCRControl_creation_sends_only_firmware_request(self):
        self.MCR, board = createMCR()
        self.assertTrue(self.MCR.boardInitialized)
        self.assertEqual(board.written, [FW_REVISION_CMD])

    def test_motor_init_without_homing_sends_no_motion(self):
        self.MCR, board = createMCR()
        self.assertTrue(self.MCR.focusInit(8390, 7959, move=False))
        self.assertTrue(self.MCR.zoomInit(3227, 3119, move=False))
        self.assertTrue(self.MCR.irisInit(75, move=False))
        self.assertTrue(self.MCR.IRCInit())
        self.assertEqual(board.motionCommands(), [])
        for motor in (self.MCR.focus, self.MCR.zoom, self.MCR.iris):
            self.assertEqual(motor.currentStep, 0)

    def test_homing_only_when_requested(self):
        # motor init defaults to move=True, so homing is an explicit part of the focusInit call (documented in the README)
        self.MCR, board = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        self.assertEqual(board.motionCommands(), [])
        board.clear()
        self.MCR.focusInit(8390, 7959)
        self.assertNotEqual(board.motionCommands(), [])
        self.assertEqual(self.MCR.focus.currentStep, 7959)

    def test_close_sends_no_motion(self):
        self.MCR, board = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        board.clear()
        closeMCR(self.MCR)
        self.assertEqual(board.motionCommands(), [])


class TestNoMotionOnErrors(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)
        err.clearErrorList()

    def test_no_board_reply_sends_no_motion(self):
        # board connected but does not reply to the firmware version request (wrong device or no power)
        board = FakeMCRBoard(fwReply=None)
        self.MCR, board = createMCR(board)
        self.assertFalse(self.MCR.boardInitialized)
        self.assertEqual(board.written, [FW_REVISION_CMD])

        # motor functions after a failed initialization return an error and send nothing
        self.assertFalse(self.MCR.focusInit(8390, 7959))
        self.assertEqual(self.MCR.focus.moveAbs(100), err.ERR_NOT_INIT)
        self.assertEqual(self.MCR.focus.moveRel(100), err.ERR_NOT_INIT)
        self.assertEqual(self.MCR.focus.home(), err.ERR_NOT_INIT)
        self.assertEqual(board.motionCommands(), [])

    def test_wrong_device_reply_sends_no_motion(self):
        # a different USB serial device that happens to reply with 7 bytes
        board = FakeMCRBoard(fwReply=b'OK\r\nhi\r')
        self.MCR, board = createMCR(board)
        self.assertFalse(self.MCR.boardInitialized)
        self.assertEqual(board.written, [FW_REVISION_CMD])

    def test_invalid_motor_init_parameters_send_no_motion(self):
        # move=True would home the motor, but the invalid steps must stop the init before any command
        self.MCR, board = createMCR()
        board.clear()
        for steps in (math.nan, None, 'abc', -1):
            with self.subTest(steps=steps):
                self.assertFalse(self.MCR.focusInit(steps, 7959, move=True))
                self.assertFalse(self.MCR.irisInit(steps, move=True))
        self.assertEqual(board.written, [])

    def test_invalid_move_parameters_send_no_motion(self):
        self.MCR, board = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        self.MCR.IRCInit()
        board.clear()
        for value in (math.nan, math.inf, None, 'abc'):
            with self.subTest(value=value):
                self.MCR.focus.moveAbs(value)
                self.MCR.focus.moveRel(value)
                self.MCR.IRC.state(value)
        self.assertEqual(board.motionCommands(), [])
        self.assertEqual(self.MCR.focus.currentStep, 0)

    def test_failed_move_keeps_step_position(self):
        # the board replies with an error after the motor is initialized: the step position must not change
        self.MCR, board = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        board._reply = lambda cmd: bytes([cmd[0], 0x01, 0x0D])
        self.assertEqual(self.MCR.focus.moveAbs(1000), err.ERR_BAD_MOVE)
        self.assertEqual(self.MCR.focus.moveRel(100), err.ERR_BAD_MOVE)
        self.assertEqual(self.MCR.focus.currentStep, 0)


class TestDeviceIdentification(unittest.TestCase):
    """PY-16: only a valid firmware-version reply initializes the module."""

    # replies that must not initialize the module: (description, reply bytes)
    INVALID_REPLIES = [
        ('no reply', None),
        ('different device, text reply', b'OK\r\nhi\r'),
        ('wrong first byte', bytes([0x75, 0x05, 0x01, 0x02, 0x03, 0x04, 0x0D])),
        ('wrong last byte', bytes([0x76, 0x05, 0x01, 0x02, 0x03, 0x04, 0x0A])),
        ('too short', bytes([0x76, 0x05, 0x01, 0x02, 0x03, 0x0D])),
        ('too long', bytes([0x76, 0x05, 0x01, 0x02, 0x03, 0x04, 0x05, 0x0D])),
        ('single byte', bytes([0x0D])),
        ('board error reply', bytes([0x74, 0x01, 0x0D])),
        ('firmware older than 5', bytes([0x76, 0x04, 0x01, 0x02, 0x03, 0x04, 0x0D])),
        ('firmware major 0', bytes([0x76, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D])),
    ]

    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)
        err.clearErrorList()

    def test_valid_reply_initializes(self):
        # case (a): the MCR board replies in the known format
        self.MCR, board = createMCR()
        self.assertTrue(self.MCR.boardInitialized)
        self.assertTrue(self.MCR.boardCommunicationState)
        self.assertEqual(board.written, [FW_REVISION_CMD])

    def test_invalid_reply_is_not_initialized(self):
        # case (b): a different USB serial device, or a board that does not reply in the known format
        for description, reply in self.INVALID_REPLIES:
            with self.subTest(reply=description):
                err.clearErrorList()
                try:
                    self.MCR, board = createMCR(FakeMCRBoard(fwReply=reply))
                except Exception as e:
                    self.fail(f'MCRControl() raised {type(e).__name__}: {e}')
                self.assertFalse(self.MCR.boardInitialized)
                self.assertIn(err.ERR_NO_COMMUNICATION, [e[0] for e in err.finalError])
                self.assertEqual(board.written, [FW_REVISION_CMD], 'data other than the firmware request was sent')
                closeMCR(self.MCR)

    def test_no_commands_after_failed_identification(self):
        # after a failed identification every public function returns an error and nothing more is sent
        self.MCR, board = createMCR(FakeMCRBoard(fwReply=bytes([0x76, 0x04, 0x01, 0x02, 0x03, 0x04, 0x0D])))
        self.assertFalse(self.MCR.boardInitialized)
        self.assertFalse(self.MCR.focusInit(8390, 7959))
        self.assertFalse(self.MCR.zoomInit(3227, 3119))
        self.assertFalse(self.MCR.irisInit(75))
        self.assertFalse(self.MCR.IRCInit())
        self.assertEqual(self.MCR.focus.moveAbs(100), err.ERR_NOT_INIT)
        self.assertEqual(self.MCR.IRC.state(1), err.ERR_NOT_INIT)
        self.assertEqual(self.MCR.MCRBoard.readBoardSN(), err.ERR_NOT_INIT)
        self.assertEqual(self.MCR.MCRBoard.setCommunicationPath('UART'), err.ERR_NOT_INIT)
        self.assertEqual(board.written, [FW_REVISION_CMD])


if __name__ == '__main__':
    unittest.main(verbosity=2)
