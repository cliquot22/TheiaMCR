"""
Fuzz testing for TheiaMCR._sendCmd function
Tests command overruns, malformed responses, and edge cases
"""

import unittest
import sys
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import time
import serial

# Add parent directory to path
sys.path.insert(0, '..')
import TheiaMCR as mcr


class TestSendCmdFuzz(unittest.TestCase):
    """Fuzz tests for _sendCmd function to test robustness against malformed inputs/outputs"""
    
    def setUp(self):
        """Set up mock serial port and MCRControl instance"""
        # Mock the serial port
        self.mock_serial = MagicMock(spec=serial.Serial)
        # Properly mock in_waiting as a property at the class level
        type(self.mock_serial).in_waiting = PropertyMock(return_value=3)
        self.mock_serial.is_open = True
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        # Create MCRControl instance with mocked serial
        with patch('serial.Serial', return_value=self.mock_serial):
            # Mock readFWRevision to return a valid firmware version
            with patch.object(mcr.MCRControl.controllerClass, 'readFWRevision', return_value='5.1.2.3.4'):
                self.mcr_instance = mcr.MCRControl(
                    serialPortName='COM_TEST',
                    moduleDebugLevel=False,
                    communicationDebugLevel=False,
                    logFiles=False
                )
        
        # Replace the serial port with our mock
        self.mcr_instance.serialPort = self.mock_serial
        self.mcr_instance.boardCommunicationState = True
        
        # Reset mock call counts after initialization
        self.mock_serial.reset_mock()
        
    def tearDown(self):
        """Clean up after tests"""
        try:
            self.mcr_instance.close()
        except:
            pass

    # ==================== Command Overrun Tests ====================
    
    def test_command_extremely_long(self):
        """Test sending extremely long command (1000 bytes)"""
        # Setup mock to return valid response
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        # Create oversized command
        long_cmd = bytearray([0x76] + [0xFF] * 999 + [0x0D])
        
        # Should still write and get response (serial port will handle overflow)
        response = self.mcr_instance.MCRBoard.com._sendCmd(long_cmd, waitTime=10)
        
        # Verify write was called with the long command
        self.mock_serial.write.assert_called_once_with(long_cmd)
        self.assertEqual(len(response), 3)
        self.assertTrue(self.mcr_instance.boardCommunicationState)
    
    def test_command_slightly_oversized(self):
        """Test command just over expected size (15 bytes vs typical 12)"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        cmd = bytearray([0x62, 0x01] + [0x00] * 13 + [0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 3)
        self.assertTrue(self.mcr_instance.boardCommunicationState)
    
    def test_command_zero_length(self):
        """Test sending zero-length command - should handle gracefully"""
        type(self.mock_serial).in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0x74, 0x01, 0x0D])
        
        cmd = bytearray()
        # Should handle empty command gracefully and return error response
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        # Should return error response and set communication state to False
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
    
    def test_command_one_byte(self):
        """Test sending single byte command"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        cmd = bytearray([0x76])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 3)

    def test_command_no_terminator(self):
        """Test command without proper 0x0D terminator"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        cmd = bytearray([0x76, 0x00])  # Missing 0x0D
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.mock_serial.write.assert_called_once()
        self.assertEqual(len(response), 3)

    # ==================== Response Overrun Tests ====================
    
    def test_response_extremely_long(self):
        """Test receiving extremely long response (1000 bytes)"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 1000])
        long_response = bytearray([0x76] + [0xFF] * 998 + [0x0D])
        self.mock_serial.readline.return_value = long_response
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        # Should return the full response (readline reads until \r or max bytes)
        self.assertEqual(len(response), 1000)
        self.assertTrue(self.mcr_instance.boardCommunicationState)
    
    def test_response_oversized_no_terminator(self):
        """Test response over 12 bytes without 0x0D terminator"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 50])
        # Response without proper terminator
        bad_response = bytearray([0x76] + [0xFF] * 49)
        self.mock_serial.readline.return_value = bad_response
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        # Should still return the response
        self.assertEqual(len(response), 50)
    
    def test_response_zero_length(self):
        """Test receiving zero-length response"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 1])
        self.mock_serial.readline.return_value = bytearray()
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 0)
    
    def test_response_one_byte(self):
        """Test receiving single byte response"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 1])
        self.mock_serial.readline.return_value = bytearray([0x76])
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 1)

    # ==================== Malformed Response Tests ====================
    
    def test_response_invalid_start_byte(self):
        """Test response with invalid start byte"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.return_value = bytearray([0xFF, 0x00, 0x0D])
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        # Should still return the response (validation happens at higher level)
        self.assertEqual(response[0], 0xFF)
    
    def test_response_all_zeros(self):
        """Test response that is all zeros"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 12])
        self.mock_serial.readline.return_value = bytearray([0x00] * 12)
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 12)
        self.assertTrue(all(b == 0x00 for b in response))
    
    def test_response_all_0xFF(self):
        """Test response that is all 0xFF"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 12])
        self.mock_serial.readline.return_value = bytearray([0xFF] * 12)
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 12)
        self.assertTrue(all(b == 0xFF for b in response))
    
    def test_response_random_bytes(self):
        """Test response with random byte values"""
        import random
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 20])
        random_response = bytearray([random.randint(0, 255) for _ in range(20)])
        self.mock_serial.readline.return_value = random_response
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 20)
    
    def test_response_with_embedded_terminators(self):
        """Test response with multiple 0x0D bytes"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 8])
        # Response with embedded 0x0D (readline should stop at first one)
        self.mock_serial.readline.return_value = bytearray([0x76, 0x0D, 0x00, 0x0D])
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        # readline typically stops at first newline/CR
        self.assertGreater(len(response), 0)

    # ==================== Timing and Timeout Tests ====================
    
    def test_response_timeout(self):
        """Test timeout when no response received"""
        # in_waiting always returns 0 to simulate no data
        type(self.mock_serial).in_waiting = PropertyMock(return_value=0)
        
        cmd = bytearray([0x76, 0x0D])
        # Use short wait time to speed up test
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=1)
        
        # Should return error response
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)
    
    def test_response_delayed(self):
        """Test response that arrives after initial wait"""
        # Simulate delayed response
        wait_count = [0]
        def delayed_in_waiting():
            wait_count[0] += 1
            return 3 if wait_count[0] > 2 else 0
        
        self.mock_serial.in_waiting = PropertyMock(side_effect=delayed_in_waiting)
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(len(response), 3)
        self.assertTrue(self.mcr_instance.boardCommunicationState)

    # ==================== Serial Port Exception Tests ====================
    
    def test_serial_exception_on_write(self):
        """Test serial exception during write"""
        self.mock_serial.write.side_effect = serial.SerialException("Write failed")
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)
    
    def test_serial_exception_on_read(self):
        """Test serial exception during read"""
        type(self.mock_serial).in_waiting = PropertyMock(side_effect=serial.SerialException("Read failed"))
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)
    
    def test_serial_exception_on_readline(self):
        """Test serial exception during readline"""
        self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, 3])
        self.mock_serial.readline.side_effect = serial.SerialException("Readline failed")
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)
    
    def test_attribute_error(self):
        """Test AttributeError (serial port is None)"""
        self.mock_serial.write.side_effect = AttributeError("Serial port not initialized")
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)

    # ==================== Special Command Tests ====================
    
    def test_special_command_set_comm_path(self):
        """Test special command 0x6B that doesn't generate response"""
        # This command should return success without reading from serial
        cmd = bytearray([0x6B, 0x00, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x6B, 0x00, 0x0D]))
        self.assertTrue(self.mcr_instance.boardCommunicationState)
        # readline should not have been called
        self.mock_serial.readline.assert_not_called()

    # ==================== Edge Case Tests ====================
    
    def test_serial_port_string_instead_of_object(self):
        """Test when serial port is a string (not initialized)"""
        # Replace serial port with string
        self.mcr_instance.serialPort = "COM_TEST_STRING" # type: ignore
        
        cmd = bytearray([0x76, 0x0D])
        response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=10)
        
        self.assertEqual(response, bytearray([0x74, 0x01, 0x0D]))
        self.assertFalse(self.mcr_instance.boardCommunicationState)
    
    def test_multiple_rapid_commands(self):
        """Test sending multiple commands rapidly"""
        self.mock_serial.in_waiting = PropertyMock(return_value=3)
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        cmd = bytearray([0x76, 0x0D])
        
        for _ in range(10):
            response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=1)
            self.assertEqual(len(response), 3)
        
        self.assertEqual(self.mock_serial.write.call_count, 10)


class TestSendCmdRandomFuzz(unittest.TestCase):
    """Random fuzz testing with completely random inputs"""
    
    def setUp(self):
        """Set up mock serial port and MCRControl instance"""
        self.mock_serial = MagicMock(spec=serial.Serial)
        # Properly mock in_waiting as a property at the class level
        type(self.mock_serial).in_waiting = PropertyMock(return_value=3)
        self.mock_serial.is_open = True
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        with patch('serial.Serial', return_value=self.mock_serial):
            # Mock readFWRevision to return a valid firmware version
            with patch.object(mcr.MCRControl.controllerClass, 'readFWRevision', return_value='5.0.0.0.0'):
                self.mcr_instance = mcr.MCRControl(
                    serialPortName='COM_TEST',
                    moduleDebugLevel=False,
                    communicationDebugLevel=False,
                    logFiles=False
                )
        
        self.mcr_instance.serialPort = self.mock_serial
        self.mcr_instance.boardCommunicationState = True
        
        # Reset mock call counts after initialization
        self.mock_serial.reset_mock()
    
    def tearDown(self):
        """Clean up after tests"""
        try:
            self.mcr_instance.close()
        except:
            pass
    
    def test_random_command_lengths(self):
        """Test 100 commands with random lengths (0-500 bytes)"""
        import random
        
        self.mock_serial.in_waiting = PropertyMock(return_value=3)
        self.mock_serial.readline.return_value = bytearray([0x76, 0x00, 0x0D])
        
        for _ in range(100):
            length = random.randint(0, 500)
            cmd = bytearray([random.randint(0, 255) for _ in range(length)])
            
            try:
                response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=1)
                # Should always return something
                self.assertIsInstance(response, bytearray)
            except Exception as e:
                self.fail(f"Unexpected exception with {length}-byte command: {e}")
    
    def test_random_response_lengths(self):
        """Test 100 responses with random lengths (0-500 bytes)"""
        import random
        
        cmd = bytearray([0x76, 0x0D])
        
        for _ in range(100):
            length = random.randint(0, 500)
            random_response = bytearray([random.randint(0, 255) for _ in range(length)])
            
            self.mock_serial.in_waiting = PropertyMock(side_effect=[0, 0, length])
            self.mock_serial.readline.return_value = random_response
            
            try:
                response = self.mcr_instance.MCRBoard.com._sendCmd(cmd, waitTime=1)
                self.assertEqual(len(response), length)
            except Exception as e:
                self.fail(f"Unexpected exception with {length}-byte response: {e}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
