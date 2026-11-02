"""
PY-10 resource exhaustion / robustness tests for TheiaMCR (CRA-RA-002).
Rapid repeated calls, memory growth, board not replying, and the USB cable unplugged (before or during a command)
and plugged back in.  Calls must return a handled error in bounded time and the module must recover after reconnect.
TheiaMCR is not thread-safe (see README) so concurrent calls from multiple threads are not tested.
"""

import gc
import time
import tracemalloc
import unittest
from unittest.mock import patch

import serial

from mock_mcr_board import createMCR, closeMCR
import TheiaMCR.errList as err

FOCUS_STEPS, FOCUS_PI = 8390, 7959
MAX_CALL_TIME = 5.0             # (s) upper bound for any single call when the board fails
MAX_MEMORY_GROWTH = 20_000      # (bytes) allowed growth over the repeated calls (allocator noise)


class _RobustnessTestCase(unittest.TestCase):
    def setUp(self):
        self.MCR, self.board = createMCR()
        self.assertTrue(self.MCR.focusInit(FOCUS_STEPS, FOCUS_PI, move=False))
        self.board.clear()
        err.clearErrorList()

    def tearDown(self):
        closeMCR(self.MCR)
        err.clearErrorList()

    def timedCall(self, func, *args, **kwargs):
        """Call func and check it returns within MAX_CALL_TIME without raising an exception."""
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            self.fail(f'{func.__name__} raised {type(e).__name__}: {e}')
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, MAX_CALL_TIME, f'{func.__name__} blocked for {elapsed:.1f} s')
        return result

    def memoryGrowth(self, func, repeats):
        """Return the memory growth (bytes) of calling func repeatedly, after a warm up."""
        for _ in range(50):
            func()
        self.board.clear()
        gc.collect()
        tracemalloc.start()
        try:
            before = tracemalloc.take_snapshot()
            for _ in range(repeats):
                func()
            self.board.clear()          # the fake board records every command, don't count it
            gc.collect()
            after = tracemalloc.take_snapshot()
        finally:
            tracemalloc.stop()
        return sum(stat.size_diff for stat in after.compare_to(before, 'filename'))


class TestRepeatedCalls(_RobustnessTestCase):
    def test_rapid_repeated_moves(self):
        for _ in range(500):
            self.assertEqual(self.MCR.focus.moveRel(100, correctForBL=False), err.ERR_OK)
            self.assertEqual(self.MCR.focus.moveRel(-100, correctForBL=False), err.ERR_OK)
        self.assertEqual(self.MCR.focus.currentStep, 0)
        self.assertEqual(len(self.board.motionCommands()), 1000)

    def test_rapid_repeated_board_queries(self):
        for _ in range(200):
            self.assertEqual(self.MCR.MCRBoard.readFWRevision(), '5.1.2.3.4')
            self.assertTrue(self.MCR.focus.readMotorSetup()[0])

    def test_no_memory_growth_on_repeated_moves(self):
        def move():
            self.MCR.focus.moveRel(10, correctForBL=False)
            self.MCR.focus.moveRel(-10, correctForBL=False)
        growth = self.memoryGrowth(move, 2000)
        self.assertLess(growth, MAX_MEMORY_GROWTH, f'memory grew {growth} bytes over 4000 moves')

    def test_no_memory_growth_on_repeated_errors(self):
        # the board replies with an error to every command.  err.finalError keeps every error until the
        # calling program reads and clears it (err.clearErrorList()) so it is cleared here to measure the rest of the module
        self.board._reply = lambda cmd: bytes([cmd[0], 0x01, 0x0D])
        def failedMove():
            self.assertEqual(self.MCR.focus.moveRel(10, correctForBL=False), err.ERR_BAD_MOVE)
            err.clearErrorList()
        # each failed move reopens the port: use a plain function (a Mock would record every call and grow)
        with patch('serial.Serial', new=lambda *args, **kwargs: self.board):
            growth = self.memoryGrowth(failedMove, 500)
        self.assertLess(growth, MAX_MEMORY_GROWTH, f'memory grew {growth} bytes over 500 failed moves')


class TestBoardNotResponding(_RobustnessTestCase):
    def test_no_reply_times_out_with_error(self):
        self.board._reply = lambda cmd: b''
        with patch('serial.Serial', return_value=self.board):
            self.assertEqual(self.timedCall(self.MCR.focus.moveRel, 10, correctForBL=False), err.ERR_BAD_MOVE)
            self.assertEqual(self.timedCall(self.MCR.MCRBoard.readFWRevision), '')
        self.assertEqual(self.MCR.focus.currentStep, 0)
        self.assertFalse(self.MCR.boardCommunicationState)

    def test_error_reply_returns_error(self):
        self.board._reply = lambda cmd: bytes([cmd[0], 0x01, 0x0D])
        with patch('serial.Serial', return_value=self.board):
            self.assertEqual(self.timedCall(self.MCR.focus.moveAbs, 1000), err.ERR_BAD_MOVE)
            self.assertFalse(self.timedCall(self.MCR.focus.writeMotorSetup, True, False, FOCUS_STEPS, 200, 2000))
        self.assertEqual(self.MCR.focus.currentStep, 0)


class TestDisconnect(_RobustnessTestCase):
    def assertUnpluggedCallsFail(self):
        # the port can't be reopened while the cable is unplugged
        with patch('serial.Serial', side_effect=serial.SerialException('could not open port')):
            for _ in range(3):
                self.assertEqual(self.timedCall(self.MCR.focus.moveRel, 100, correctForBL=False), err.ERR_BAD_MOVE)
            self.assertEqual(self.timedCall(self.MCR.focus.moveAbs, 1000), err.ERR_BAD_MOVE)
            self.assertEqual(self.timedCall(self.MCR.MCRBoard.readFWRevision), '')
        self.assertFalse(self.MCR.boardCommunicationState)

    def assertRecoversAfterPlugIn(self, expectedStep):
        # after the cable is plugged in the module reopens the port and moves work again (within 2 calls)
        self.board.plugIn()
        restarts = self.MCR.boardCommunicationRestarts
        with patch('serial.Serial', return_value=self.board):
            results = [self.timedCall(self.MCR.focus.moveRel, 100, correctForBL=False) for _ in range(2)]
        self.assertIn(err.ERR_OK, results, 'module did not recover after the board was plugged in')
        self.assertGreater(self.MCR.boardCommunicationRestarts, restarts)
        self.assertEqual(self.MCR.focus.currentStep, expectedStep + 100 * results.count(err.ERR_OK))

    def test_unplug_between_commands(self):
        self.assertEqual(self.MCR.focus.moveRel(500, correctForBL=False), err.ERR_OK)
        self.board.unplug()
        self.assertUnpluggedCallsFail()
        self.assertEqual(self.MCR.focus.currentStep, 500)
        self.assertRecoversAfterPlugIn(500)

    def test_unplug_during_command(self):
        # the move command reaches the board but the cable is unplugged before the reply.  The module reports
        # the move failed and keeps the last known step; the lens should be homed again after reconnecting
        self.board.unplugAfterNextWrite = True
        with patch('serial.Serial', side_effect=serial.SerialException('could not open port')):
            self.assertEqual(self.timedCall(self.MCR.focus.moveRel, 500, correctForBL=False), err.ERR_BAD_MOVE)
        self.assertEqual(len(self.board.motionCommands()), 1)
        self.assertEqual(self.MCR.focus.currentStep, 0)
        self.assertUnpluggedCallsFail()
        self.assertRecoversAfterPlugIn(0)

    def test_home_after_reconnect(self):
        self.board.unplug()
        self.assertUnpluggedCallsFail()
        self.board.plugIn()
        with patch('serial.Serial', return_value=self.board):
            results = [self.timedCall(self.MCR.focus.home) for _ in range(2)]
        self.assertIn(err.ERR_OK, results)
        self.assertEqual(self.MCR.focus.currentStep, FOCUS_PI)


if __name__ == '__main__':
    unittest.main(verbosity=2)
