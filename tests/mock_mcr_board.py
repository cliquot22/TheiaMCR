"""
Byte-level stand-in for the MCR board serial port used by the unit tests.
The module code (readFWRevision, _sendCmd, response parsing) runs unchanged; only the serial port is replaced.
Every command written to the port is recorded so tests can check exactly what would be sent to the board.
"""

import itertools
import os
import sys
from unittest.mock import patch

import serial

# make the TheiaMCR package in this repository importable when the tests are run from any folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import TheiaMCR as mcr

# firmware commands that move a motor (see the motor control documentation)
MOTION_COMMANDS = {0x62, 0x66, 0x73}
FW_REVISION_CMD = bytes([0x76, 0x0D])
FW_REVISION_REPLY = bytes([0x76, 0x05, 0x01, 0x02, 0x03, 0x04, 0x0D])    # firmware 5.1.2.3.4

_portNumbers = itertools.count(1)


class FakeMCRBoard:
    """Replaces serial.Serial.  Replies to each command the way a working MCR board would."""

    def __init__(self, fwReply=FW_REVISION_REPLY):
        self.fwReply = fwReply          # None: the board does not reply to the firmware version request
        self.written = []               # every command written, as bytes
        self._pending = b''
        self.is_open = True
        self.connected = True           # False: the USB cable is unplugged, port access raises SerialException
        self.unplugAfterNextWrite = False   # True: the cable is unplugged after the next command is written (mid-command)

    # serial.Serial interface used by TheiaMCR
    @property
    def in_waiting(self):
        self._checkConnected()
        return len(self._pending)

    def write(self, data):
        self._checkConnected()
        cmd = bytes(data)
        self.written.append(cmd)
        self._pending = self._reply(cmd)
        if self.unplugAfterNextWrite:
            self.unplug()
        return len(cmd)

    def readline(self):
        self._checkConnected()
        reply, self._pending = self._pending, b''
        return bytearray(reply)

    def flush(self): pass
    def reset_input_buffer(self): self._pending = b''
    def reset_output_buffer(self): pass
    def close(self): self.is_open = False

    def _reply(self, cmd):
        code = cmd[0]
        if code == 0x76:
            return self.fwReply or b''
        if code == 0x67:
            # read motor setup: stepper, wide/far stop, max steps 8390, speeds 100-1500
            return bytes([0x67, cmd[1], 0x00, 0x01, 0x00, 0x20, 0xC6, 0x00, 0x64, 0x05, 0xDC, 0x0D])
        if code == 0x79:
            return bytes([0x79, 0x05, 0x50, 0x00, 0x00, 0x80, 0x95, 0x0D])
        if code == 0x6B:
            return b''                  # set communication path has no reply
        return bytes([code, 0x00, 0x0D])

    def _checkConnected(self):
        if not self.connected:
            raise serial.SerialException('device disconnected')

    # helpers for the tests
    def unplug(self):
        self.connected = False
        self.unplugAfterNextWrite = False
        self._pending = b''

    def plugIn(self):
        self.connected = True
        self.is_open = True

    def motionCommands(self):
        return [c for c in self.written if c and c[0] in MOTION_COMMANDS]

    def clear(self):
        self.written.clear()


def createMCR(board=None):
    """
    Create an MCRControl instance connected to a FakeMCRBoard on a unique port name (MCRControl keeps one instance per port).
    ### return: [MCRControl instance, FakeMCRBoard]
    """
    board = board or FakeMCRBoard()
    with patch('serial.Serial', return_value=board):
        MCR = mcr.MCRControl(f'COM_FAKE{next(_portNumbers)}', logFiles=False)
    return MCR, board


def closeMCR(MCR):
    """Close the instance and remove it from the MCRControl port cache."""
    try:
        MCR.close()
    except Exception:
        pass
    mcr.MCRControl._instances.pop(getattr(MCR, 'serialPortName', None), None)
