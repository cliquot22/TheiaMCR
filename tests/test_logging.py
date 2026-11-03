"""
SW-13 logging and error output tests for TheiaMCR (CRA-RA-002).
- Connect, disconnect, close and rejected-command events are logged through the TheiaMCR logger at the expected level.
- The module adds handlers only to its own logger and never to the calling program's root logger.
- Messages at INFO level and above contain no user name or home folder path, and board command bytes are not
  logged unless communicationDebugLevel=True.
"""

import contextlib
import errno
import io
import logging
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import serial

from mock_mcr_board import FakeMCRBoard, createMCR, closeMCR, mcr

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGGER_NAME = mcr.TheiaMCR.MCRControl.log.name
HOME = os.path.expanduser('~')
USER_NAME = os.path.basename(HOME)

# run in a separate Python process so the root logger starts with no handlers
ROOT_HANDLER_CHECK = r'''
import logging, math, serial
from unittest.mock import patch
from mock_mcr_board import createMCR
import TheiaMCR.errList as err
counts = [len(logging.root.handlers)]
MCR, board = createMCR()
counts.append(len(logging.root.handlers))
MCR.focusInit(8390, 7959, move=False)
MCR.focus.moveRel(math.nan)                     # rejected command
counts.append(len(logging.root.handlers))
board.unplug()
with patch('serial.Serial', side_effect=serial.SerialException('could not open port')):
    MCR.focus.moveRel(10)                       # failed move, saves errors
counts.append(len(logging.root.handlers))
print(counts)
'''


class _FakeLogFiles(logging.Handler):
    """Stands in for rotatingLogFiles so no log files are written; the file names are in the user's home folder."""
    def __init__(self, logger, nameKey='', maxLines=10000):
        super().__init__()
        folder = os.path.join(HOME, 'AppData', 'Local', 'TheiaMCR', 'log')
        self.filenames = [os.path.join(folder, f'logA-{nameKey}.txt'), os.path.join(folder, f'logB-{nameKey}.txt')]

    def emit(self, record):
        pass


class TestHandlers(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)

    def test_import_adds_no_handlers(self):
        check = 'import logging, TheiaMCR; print(len(logging.root.handlers))'
        run = subprocess.run([sys.executable, '-c', check], cwd=os.path.dirname(TESTS_DIR), capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), '0', 'importing TheiaMCR added a handler to the root logger')

    def test_only_console_handler_without_log_files(self):
        # logFiles=False: the module's own logger gets one console handler and nothing else
        self.MCR, _ = createMCR()
        handlers = logging.getLogger(LOGGER_NAME).handlers
        self.assertEqual(len(handlers), 1, handlers)
        self.assertIsInstance(handlers[0], logging.StreamHandler)
        self.assertNotIsInstance(handlers[0], logging.FileHandler)

    def test_no_root_handler_added(self):
        run = subprocess.run([sys.executable, '-c', ROOT_HANDLER_CHECK], cwd=TESTS_DIR, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip().splitlines()[-1], '[0, 0, 0, 0]',
                         'root logger handler count after import, MCRControl(), rejected command, failed move')

    def test_calling_program_can_collect_messages(self):
        # the calling program adds its own handler to the TheiaMCR logger
        self.MCR, _ = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        records = []
        collector = logging.Handler(logging.WARNING)
        collector.emit = records.append
        logger = logging.getLogger(LOGGER_NAME)
        logger.addHandler(collector)
        try:
            self.MCR.focus.moveRel(math_nan())
        finally:
            logger.removeHandler(collector)
        self.assertTrue(any('Invalid moveRel steps' in r.getMessage() for r in records), [r.getMessage() for r in records])


class TestEventLogging(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)

    def messages(self, logs, level=logging.DEBUG):
        return [r.getMessage() for r in logs.records if r.levelno >= level]

    def test_connect_logged_at_info(self):
        with self.assertLogs(LOGGER_NAME, logging.INFO) as logs:
            self.MCR, _ = createMCR()
        self.assertTrue(any('opened' in m for m in self.messages(logs)), self.messages(logs))

    def test_board_identification_logged_at_info(self):
        with self.assertLogs(LOGGER_NAME, logging.INFO) as logs:
            self.MCR, _ = createMCR()
        self.assertIn('FW revision: 5.1.2.3.4', self.messages(logs))

    def test_failed_identification_logged_at_error(self):
        with self.assertLogs(LOGGER_NAME, logging.ERROR) as logs:
            self.MCR, _ = createMCR(FakeMCRBoard(fwReply=None))
        self.assertTrue(any('No response' in m for m in self.messages(logs)), self.messages(logs))

    def test_rejected_command_logged_at_warning(self):
        self.MCR, _ = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        with self.assertLogs(LOGGER_NAME, logging.WARNING) as logs:
            self.MCR.focus.moveRel(math_nan())
            self.MCR.focus.setMotorSpeed(5000)
            self.MCR.IRC.state(3)
        messages = self.messages(logs)
        self.assertTrue(any('Invalid moveRel steps' in m for m in messages), messages)
        self.assertTrue(any('outside range' in m for m in messages), messages)

    def test_disconnect_logged_at_error(self):
        self.MCR, board = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        board.unplug()
        with self.assertLogs(LOGGER_NAME, logging.WARNING) as logs:
            with patch('serial.Serial', side_effect=serial.SerialException('could not open port')):
                self.MCR.focus.moveRel(10, correctForBL=False)
        errors = self.messages(logs, logging.ERROR)
        self.assertTrue(any('Serial port' in m for m in errors), errors)
        self.assertTrue(any('Rechecking MCR board communication' in m for m in self.messages(logs)), self.messages(logs))

    def test_close_logged_at_info(self):
        self.MCR, _ = createMCR()
        with self.assertLogs(LOGGER_NAME, logging.INFO) as logs:
            closeMCR(self.MCR)
        self.assertTrue(any('closed' in m for m in self.messages(logs)), self.messages(logs))


class TestNoSensitiveDetail(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, 'MCR'):
            closeMCR(self.MCR)

    def assertNoHomeFolder(self, messages):
        for message in messages:
            with self.subTest(message=message):
                self.assertNotIn(HOME.lower(), message.lower())
                self.assertNotIn(f'\\{USER_NAME}\\'.lower(), message.lower())
                self.assertNotIn(f'/{USER_NAME}/'.lower(), message.lower())

    def test_session_messages_have_no_home_folder(self):
        # a normal session with errors, at INFO level and above
        with self.assertLogs(LOGGER_NAME, logging.INFO) as logs:
            self.MCR, board = createMCR()
            self.MCR.focusInit(8390, 7959, move=False)
            self.MCR.focus.moveRel(100)
            self.MCR.focus.moveRel(math_nan())
            board.unplug()
            with patch('serial.Serial', side_effect=serial.SerialException('could not open port')):
                self.MCR.focus.moveRel(10, correctForBL=False)
            closeMCR(self.MCR)
        self.assertNoHomeFolder([r.getMessage() for r in logs.records])

    def test_log_file_path_message_has_no_home_folder(self):
        board = FakeMCRBoard()
        with self.assertLogs(LOGGER_NAME, logging.INFO) as logs:
            with patch('serial.Serial', return_value=board), patch.object(mcr.TheiaMCR.rotLogFiles, 'rotatingLogFiles', _FakeLogFiles):
                self.MCR = mcr.MCRControl('COM_LOGTEST', logFiles=True)
        self.assertNoHomeFolder([r.getMessage() for r in logs.records])

    def test_long_caller_value_is_shortened(self):
        # a very long rejected value must not fill the log
        self.MCR, _ = createMCR()
        self.MCR.focusInit(8390, 7959, move=False)
        with self.assertLogs(LOGGER_NAME, logging.WARNING) as logs:
            self.MCR.focus.moveRel('x' * 10000)
        message = next(r.getMessage() for r in logs.records if 'Invalid moveRel steps' in r.getMessage())
        self.assertLess(len(message), 200, message)
        self.assertIn('(10002 characters)', message)

    def test_log_folder_error_logged_without_path(self):
        # the log folder can't be created: a warning through logging (not print), without the folder path
        folder = os.path.join(HOME, 'AppData', 'Local', 'TheiaMCR', 'log')
        error = PermissionError(errno.EACCES, 'Access is denied', folder)
        rotLogFiles = mcr.TheiaMCR.rotLogFiles
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), patch.object(rotLogFiles.os, 'makedirs', side_effect=error):
            with self.assertLogs(rotLogFiles._log.name, logging.WARNING) as logs:
                result = rotLogFiles.rotatingLogFiles.createLogFilenames(None, 'COM3')
        self.assertEqual(result, [None, None])
        self.assertEqual(stdout.getvalue(), '', 'print() was used')
        self.assertTrue(any('log folder' in r.getMessage() for r in logs.records))
        self.assertNoHomeFolder([r.getMessage() for r in logs.records if r.levelno >= logging.INFO])

    def test_command_bytes_not_logged_by_default(self):
        with self.assertLogs(LOGGER_NAME, logging.DEBUG) as logs:
            self.MCR, _ = createMCR()
            self.MCR.focusInit(8390, 7959, move=False)
            self.MCR.focus.moveRel(100)
        messages = [r.getMessage() for r in logs.records]
        self.assertFalse([m for m in messages if m.strip().startswith(('->', '<-'))], 'board command bytes were logged')


def math_nan():
    return float('nan')


if __name__ == '__main__':
    unittest.main(verbosity=2)
