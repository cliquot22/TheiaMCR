# Theia Technologies MCR control module
# This module allows the user to control the MCR600 series lens control boards.  There are functions to
# initialize the board and motors and to control the movements (relative, absolute, etc).  
# The board must be initizlized first using the MCRControl __init__ function.  Then the motors must
# all be initialize with their steps and limit positions.  The init commands will create instances
# of the motor class for each motor.  
#
# (c) 2023 Theia Technologies
# www.TheiaTech.com
# BSD 3-clause license applies

import serial
import time
import TheiaMCR.errList as err
import logging as log
from typing import Tuple, Union

# internal constants used across the classes in this module.  
RESPONSE_READ_TIME = 500                # (ms) max time for the MCR to post a response in the buffer
OK = 0
MCR_FOCUS_MOTOR_ID = 0x01               # motor ID's as specified in the motor control documentation
MCR_ZOOM_MOTOR_ID = 0x02
MCR_IRIS_MOTOR_ID = 0x03
MCR_IRC_MOTOR_ID = 0x04
MCR_IRC_SWITCH_TIME = 50              # (ms) switch time for IRC
MCR_FZ_DEFAULT_SPEED = 1000           # (pps) default focus/zoom motor speeds
MCR_FZ_HOME_SPEED = 1200              # (pps) speed to travel to home PI position
MCR_IRIS_DEFAULT_SPEED = 100          # (pps) default iris motor speed
MCR_BACKLASH_OVERSHOOT = 60           # used to remove lens backlash, this should exceed lens maximum backlash amount
MCR_HARDSTOP_TOLERANCE = 100          # additional move amount to be sure to pass home position from hard stop
MCR_MOVE_REST_TIME = 0.05             # (s) rest time between moves

#####################################################################################
# MCRControl class
class MCRControl():
    serialPort = 'com4'
    MCRInitialized = False

    MCRBoard = None         # controller board instance
    focus = None            # motor types
    zoom = None
    iris = None
    
    # MCRInit
    def __init__(self, com:str):
        '''
        This class is used for interacting with the Theia MCR motor control boards. 
        Initialize the MCR board (this class) before any commands can be sent.  
        Successful initialization is confirmed by receiving the board firmware version from the board.  
        Motor initialization (focusInit, zoomInit, irisInit) must be called separately for each motor. 

        This is the top level class for all interactions with the MCR600 series boards
        ### input: 
        - com: the com port name of the board (e.g. "com21").  The com port name is formatted for Windows.  
        ### Public functions: 
        - __init__(self, com:str)
        - focusInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool
        - zoomInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool
        - irisInit(self, steps:int, move:bool=True) -> bool
        - IRCInit(self) -> bool
        - IRCState(self, state:bool) -> int
        ### class variables
        - MCRInitialized: set when the board is successfully initialized (not the motors)
        ### Sub-classes: 
        - motor
        - board

        (c)2023 Theia Technologies
        www.TheiaTech.com
        '''
        success = 0
        if self.MCRInitialized:
            success = 1
        else:
            # initialize board
            try:
                self.serialPort = serial.Serial(port = com, baudrate=115200, bytesize=8, timeout=0.1, stopbits=serial.STOPBITS_ONE)
                success = int(com[3:])
                log.debug(f'Comport {success} communication success')
            except serial.SerialException as e:
                log.error("Serial port not open {}".format(e))
                err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                success = err.ERR_SERIAL_PORT

            # send a test command to the board to read FW version
            self.controllerClass.serialPort = self.serialPort
            self.MCRBoard = self.controllerClass()
        response = self.MCRBoard.readFWRevision()
        if int(response.rsplit('.', -1)[0]) < 5:
            log.error("Error: No resonse received from MCR controller")
            err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
            success = err.ERR_NO_COMMUNICATION
        self.MCRInitialized = True if success >= 0 else False

        # added for Mathlab initialization
        self.focus = None 
        self.zoom = None
        self.iris = None

    # Motor initialization
    def focusInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool:
        '''
        Initialize the parameters of the motor.  This must be called after the board is initialized.  
        ### input: 
        - steps: maximum number of steps
        - pi: pi location in step number
        - move: (optional, True) move motor to home position or (False) initialize without moving. 
        - accel: (optional, 0) motor acceleration steps (check motor control documentation to see if this variable is supported in firmware)
        ### return: 
        [True] if motor initialization was successful
        '''
        self.focus = self.motor(MCR_FOCUS_MOTOR_ID, steps, pi, move, accel)
        return self.focus.initialized
    
    def zoomInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool:
        '''
        Initialize the parameters of the motor.  This must be called after the board is initialized.  
        ### input: 
        - steps: maximum number of steps
        - pi: pi location in step number
        - move: (optional, True) move motor to home position or (False) initialize without moving. 
        - accel: (optional, 0) motor acceleration steps (check motor control documentation to see if this variable is supported in firmware)
        ### return: 
        [True] if motor initialization was successful
        '''
        self.zoom = self.motor(MCR_ZOOM_MOTOR_ID, steps, pi, move, accel)
        return self.zoom.initialized
    
    def irisInit(self, steps:int, move:bool=True) -> bool:
        '''
        Initialize the parameters of the motor.  This must be called after the board is initialized.  
        ### input: 
        - steps: maximum number of steps
        - move: (optional, True) move motor to home position or (False) initialize without moving. 
        ### return: 
        [True] if motor initialization was successful
        '''
        self.iris = self.motor(MCR_IRIS_MOTOR_ID, steps, 0, move, 0)
        return self.iris.initialized

    # IRCInit
    def IRCInit(self) -> bool:
        '''
        Initialize the parameters of the IRC motor.  
        For the IRC switch motor: maximum 1000 steps allows 1 second activation time (at speed 1000pps).  The activation
        time is set by the number of steps (1 step = 1 ms).  See the motor control docuemtation for more info.  
        ### return: 
        [initizlized success]
        '''
        success = self.MCRBoard.MCRMotorInit(MCR_IRC_MOTOR_ID, pi=0, steps=1000, speedRange=1, DCMotorType=True)
        #####_err = self.motor(MCR_IRC_MOTOR_ID, steps=1000, pi=0, DCMotorType=True, move=False)
        return success

    # IRCState
    def IRCState(self, state:int) -> int:
        '''
        Set the IRC state to either visible or clear filter (or other options depending on the lens model)
        ### input: state: [  
        1: Visible (IR blocking) filter 1 |  
        2: clear filter 2  
        ]
        ### return: 
        [new state (1 | 2)]
        '''
        sw = MCR_IRC_SWITCH_TIME  ## move in positive direction
        if state == 1:
            sw *= -1                ## move in negative direction
        self.MCRBoard.MCRMove(MCR_IRC_MOTOR_ID, steps=sw, speed=1000)
        return state

    ######################################################################################################
    # Motor definition class
    class motor():
        motorID = 0x00              # motor ID (0x01 ~ 0x04) for controller, see the motor controller documentation.  
        initialized = False

        currentStep = 0
        currentSpeed = 1000
        PIStep = 0                  # step position of PI limit switch
        PISide = 0                  # high (1) or low (-1) side of step range for limit switch
        maxSteps = 0
        acceleration = 0            # motor acceleration to start/stop each step.  Check documentation to see
                                    # if acceleration is supported in the firmware.  
        respectLimits = True        # Set (True) to prevent motor from going past PI limit switch position.  

        MCRBoard = None

        # initialize the parameters of the motor
        def __init__(self, motorID:bytes, steps:int, pi:int, move:bool=True, accel:int=0, DCMotorType:bool=False):
            '''
            The class is used for the focus, zoom, and iris motors.  The only difference between these motors are speeds and number of steps.  
            ### Public functions: 
            - __init__(self, motorID:bytes, steps:int, pi:int, move:bool=True, accel:int=0, DCMotorType:bool=False)
            - home(self) -> int
            - moveAbs(self, step:int) -> int
            - moveRel(self, steps:int, correctForBL:bool=True) -> int
            - setMotorSpeed(self, speed) -> int
            - setRespectLimits(self, state:bool)
            ### input: 
            - motorID: byte value for the motor (0x01 ~ 0x04).  See the motor control documentation.  
                - 0x01: focus
                - 0x02: zoom
                - 0x03: iris
                - 0x04: IRC (DC motor)
            - steps: maximum number of steps
            - pi: pi location in step number
            - move: (optional, True) move motor to home position after initializing
            - accel: (optional, 0) motor acceleration steps.  Check the documentation to see if acceleration is supported in the firmware.  
            - DCMotorType (optional: False): set True if the motor is DC motor type otherwise (False) is it a stepper
            ### class variables
            - initialized
            - currentStep
            - currentSpeed
            - PIStep (step position of the photo interrupter limit switch)
            - maxSteps
            - respectLimits (set True to prevent motor from exceeding limits)
            - MCRBoard (the control board instance)
            ### Private functions:
            - checkLimits(self, steps:int, limitStep:bool=False) -> int
            '''
            self.motorID = motorID
            self.PIStep = pi
            self.maxSteps = steps
            # set acceleration
            self.acceleration = accel << 3 | 0x01

            # set PI side
            if (steps - pi) < pi:
                self.PISide = 1
            else:
                self.PISide = -1

            # set the motor speed range
            speedRange = 0
            if motorID == MCR_FOCUS_MOTOR_ID or motorID == MCR_ZOOM_MOTOR_ID:
                self.currentSpeed = MCR_FZ_DEFAULT_SPEED
                speedRange = 1
            else:
                self.currentSpeed = MCR_IRIS_DEFAULT_SPEED

            # initialize the motor control board instance for sending the commands
            self.MCRBoard = MCRControl.controllerClass()
            success = self.MCRBoard.MCRMotorInit(self.motorID, pi=pi, steps=steps, speedRange=speedRange, DCMotorType=DCMotorType)
            if not success:
                log.error('Motor not initialized')
                err.saveError(err.ERR_NOT_INIT, err.MOD_MCR, err.errLine())
            else:
                self.currentStep = 0
                error = OK
            self.initialized = success

            # move the motor to the home position (PI limit switch)
            if move and motorID != MCR_IRC_MOTOR_ID:
                error = self.home()
                if error != 0:
                    err.saveError(error, err.MOD_MCR, err.errLine())

        # Home
        def home(self) -> int:
            '''
            Send the motor to the PI location by moving 110% of the maximum number of steps.  Jog back and forth by the difference 
            between max steps (or min steps) and the PI step to be sure to set the motor to the correct side of the PI trigger 
            (if the PI exists).  
            The motor will automatically and instantly stop at the PI locaiton.  The respectLimits variable will be reset
            to the original value after doing the home movement.  
            ### input:
            - none
            ### globals: 
            - set currentStep
            - read currentSpeed
            ### return: 
            [
                OK = 0 | 
                err_bad_move: (PI was nto set or triggered (call motorInit first))
            ]
            '''
            # determine direction of PI
            steps = (self.maxSteps * 1.1) * self.PISide

            # store current state of limit switches
            setIgnoreLimitsToFalse = False
            if not self.respectLimits:
                # reset respectLimits back to false after home
                setIgnoreLimitsToFalse = True
                self.setRespectLimits(True)
            
            # move the motor to expected PI position
            success = self.MCRBoard.MCRMove(self.motorID, steps=steps, speed=max(self.currentSpeed, MCR_FZ_HOME_SPEED), acceleration=self.acceleration)
            if self.motorID == 0x01 or self.motorID == 0x02:
                # confirm the motor is at the PI and not past the PI position, add an additional 100 steps over the expected (max - PIStep) difference to be sure since the physical max step is variable.  
                piCheckSteps = (self.PIStep - self.maxSteps) if self.PISide == 1 else self.PIStep
                time.sleep(MCR_MOVE_REST_TIME)
                self.MCRBoard.MCRMove(self.motorID, steps=(piCheckSteps - self.PISide * MCR_HARDSTOP_TOLERANCE), speed=max(self.currentSpeed, MCR_FZ_HOME_SPEED), acceleration=self.acceleration)
                time.sleep(MCR_MOVE_REST_TIME)
                success = self.MCRBoard.MCRMove(self.motorID, steps=-(piCheckSteps - self.PISide * MCR_HARDSTOP_TOLERANCE * 2), speed=max(self.currentSpeed, MCR_FZ_HOME_SPEED), acceleration=self.acceleration)

            # reset the respect limit state
            if setIgnoreLimitsToFalse: self.setRespectLimits(False)
            if success:
                self.currentStep = self.PIStep
            else:
                log.error(f"Error: Motor 0x{self.motorID:02X} move error")
                err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
                return err.ERR_BAD_MOVE
            return OK
        
        # moveAbs
        def moveAbs(self, step:int) -> int:
            '''
            Move the motor to the home position then to the absolute step number.  The step must be an integer
            step number.  If self.respectLimits is True, the target step must not exceed the PI step position.  
            If the self.respectLimits is False, the target must be within the min-max step range.  

            Backlash will be accounted for if the move is away from the PI location.  If the move exceeds the PI location, 
            the backlash may not be accounted for due to limited number of steps available in the range.  If the target is 
            step 8500 and the maximum steps are 8510 then only 10 steps of backlash are available which may not be enough 
            to fully account for backlash.  
            ### input: 
            - step: the final target step to move to.
            ### return: 
            [
                OK = 0 | 
                err_bad_move: if there is a home error | 
                err_param: if there is an input error
            ]
            '''
            if step < 0:
                log.warning("Warning: target motor step < 0")

            # move to PI position
            error = self.home()
            if error != 0:
                log.error("Error: focus home error")
                err.saveError(error, err.MOD_MCR, err.errLine())
                return error

            # move to absolute position
            steps = step - self.PIStep
            error = self.moveRel(steps)
            if error != 0:
                # propogate error
                err.saveError(error, err.MOD_MCR, err.errLine())
                return error
            return OK
        
        # moveRel
        def moveRel(self, steps:int, correctForBL:bool=True) -> int:
            '''
            Move the motor by a number of steps.  This can be positive or negative movement.  
            By default this will compensate for backlash in the motor when moving towards the PI limit position.  
            If the target is within the backlash compenstation step number (i.e. <60 away from the 
            home PI position) then the backlash correction will be limited 
            to the difference between the home PI position (or min/max step if the PI is not regarded) and the 
            target step.  

            If the limits are regarded the motor won't go beyond the limit switch.  If they are not regarded, 
            the motor could go beyond the min/max steps (i.e. the hard stop).  If it does then 
            the step counter will be off and the motor will have to be home initialized.  
            ### input: 
            - steps: the number of steps to move
            - correctForBL (optional, True): set true to compensate for backlash when moving away from PI limit switch.  
            ### return: 
            [
                OK = 0 |
                err_bad_move: if there is a move error 
            ]
            '''
            if steps == 0:
                return OK

            # check for limits
            limit, steps = self.checkLimits(steps, self.respectLimits)
            if self.respectLimits and (limit != 0):
                log.warn(f'Limiting focus relative steps to {steps}')

            # move the motor
            success = False
            blCorrection = MCR_BACKLASH_OVERSHOOT
            if correctForBL and (steps * self.PISide > 0):
                # moving towards PI, add backlash adjustment and keep any moves within PI limit or min/max limits
                blCorrection = max(0,min(MCR_BACKLASH_OVERSHOOT, self.PIStep * ((self.PIStep if self.respectLimits else (self.maxSteps if self.PIStep > 0 else 0)) - (steps + self.currentStep))))

                success = self.MCRBoard.MCRMove(self.motorID, steps + self.PISide * blCorrection, self.currentSpeed, self.acceleration)
                if blCorrection > 0: 
                    # move back by the BL correction amount
                    time.sleep(MCR_MOVE_REST_TIME)
                    success = self.MCRBoard.MCRMove(self.motorID, -self.PISide * blCorrection, self.currentSpeed, self.acceleration)
            else:
                # no need for backlash adjustment
                success = self.MCRBoard.MCRMove(self.motorID, steps, self.currentSpeed, self.acceleration)
                
            self.currentStep += steps
            if not success:
                err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
                return err.ERR_BAD_MOVE
            return OK
        
        # setRespectLimits
        def setRespectLimits(self, state:bool):
            '''
            Set the flag to stop motor moves at the PI limits or to continue past the limits.  In some cases
            the limits should be turned off to get to the target motor position.  
            ### input: 
            - state: set or remove the limit
            ### globals: 
            - set the respectLimits class variable.  
            '''
            log.info(f'PI limit for motor 0x{self.motorID:02X} set to {state}')
            self.respectLimits = state
            self.MCRBoard.MCRRegardLimits(self.motorID, state, self.PISide)

        # setMotorSpeed
        def setMotorSpeed(self, speed) -> int:
            '''
            Set the motor speed.  It should be in the range.  
            ### input: 
            - speed: speed to set [pps]
            ### globals: 
            - set currentSpeed
            ### return: 
            [
                OK = 0 |
                err_range, out of acceptable range 
            ]
            '''
            if self.motorID in {MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID}:
                if speed > 1500 or speed < 100:
                    log.warning(f'Requested speed {speed} is outside range 100-1500')
                    return err.ERR_RANGE
            elif self.motorID == MCR_IRIS_MOTOR_ID:
                if speed > 200 or speed < 10:
                    log.warning(f'Requested speed {speed} is outside range 10-200')
                    return err.ERR_RANGE
            self.currentSpeed = speed
            return OK

        #-----internal functions------------------------------
        # checkLimits
        def checkLimits(self, steps:int, limitStep:bool=False) -> int:
            '''
            Check if the target step will exceed limits or hard stop positions.  
            if limitStep is True the requested step number will be changed so it doesn't exceed
            the PI limit switch or hard stop positions.  If it is set to False, there will only be a 
            warning but the number of steps won't be changed.  
            ### input: 
            - steps: target steps
            - limitStep: (optional, False) set True to limit steps, False to only warn
            ### return: 
            [
                return value (
                    2: steps exceed maximum steps  |
                    1: steps exceed high PI  |
                    0: steps will not cause exceeding limits |
                    -1: steps exceed low PI  |
                    -2: steps exceed minimum steps),
                corrected number of steps
            ]
            '''
            retSteps = steps
            retVal = 0
            if limitStep and (self.PISide > 0) and (self.currentStep + steps > self.PIStep):
                if limitStep:
                    retSteps = max(self.PIStep - self.currentStep, 0)
                log.warning(f"Warn: steps exceeds PI {self.PIStep}")
                retVal = 1
            elif limitStep and (self.PISide < 0) and (self.currentStep + steps < self.PIStep):
                if limitStep:
                    retSteps = min(self.PIStep - self.currentStep, 0)
                log.warning(f"Warn: steps exceeds low PI {self.PIStep}")
                retVal = -1
            elif self.currentStep + steps > self.maxSteps:
                if limitStep:
                    retSteps = max(self.maxSteps - self.currentStep, 0)
                log.warning(f"Warn: steps exceeds maximum {self.maxSteps}")
                retVal = 2
            elif self.currentStep + steps < 0:
                if limitStep:
                    retSteps = min(-self.currentStep, 0)
                log.warning(f"Warn: steps exceeds minimum 0")
                retVal = -2
            return retVal, retSteps

    ###################################################################################################
    # Controller board functions
    class controllerClass():
        serialPort = 'com4'

        # initialize the control board 
        # NOTE: the serialPort variable must be set before using any functions. 
        def __init__(self):
            '''
            This class formats the user commands into byte string commands for the MCR600 series board protocol.  
            The controller board class variable 'serialPort' must be set before any functions are available. 
            The serial port name is formatted as a Windows vitual com port ("com4")
            ### Public functions: 
            - __init__(self)
            - readFWRevision(self) -> str
            - readBoardSN(self) -> str
            ### input
            - none
            ### class variables
            - none
            ### Private functions: 
            - MCRMotorInit(self, id:int, steps:int, pi:int, speedRange:int, DCMotorType:bool=False) -> bool
            - MCRMove(self, id:int, steps:int, speed:int, acceleration:int=0) -> bool
            - MCRRegardLimits(self, id:int, state:bool=True, PISide:int=1) -> bool
            - MCRSendCmd(self, cmd, waitTime:int=10)
            '''
            pass

        # ----------- board information --------------------
        # get the FW revision from the board
        def readFWRevision(self) -> str:
            '''
            Get FW revision on the board. 
            Replies with string value of the firmware revision response
            ### return: 
            [string representing the FW revision (ex. '5.3.1.0.0')]
            '''
            response = ""
            cmd = bytearray(2)
            cmd[0] = 0x76
            cmd[1] = 0x0D
            response = self.MCRSendCmd(cmd)
            fw = ''
            if response == None:
                log.error("Error: No resonse received from MCR controller")
                err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
            else:
                fw = (".".join("{:x}".format(c) for c in response))
                fw = fw[3:-2]
                log.info(f"FW revision: {fw}")
            return fw

        # get the board SN
        def readBoardSN(self) -> str:
            '''
            Get the serial number of the board. 
            Replies with a string representing the board serial number read from the response
            board response is hex digits interpreted (not converted) as decimal in a very specific format (ex. '055-001234')
            ### return: 
            [string with serial number]
            '''
            response = ""
            cmd = bytearray(2)
            cmd[0] = 0x79
            cmd[1] = 0x0D
            response = self.MCRSendCmd(cmd)
            sn = ''
            if response == None:
                log.error("Error: No resonse received from MCR controller")
                err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
            else:
                sn = f'{response[1]:02x}{response[2]:02x}'
                sn = sn[:-1]
                sn += f'-00{response[-3]:x}{response[-2]:x}'
                #sn = ''.join(f'{c:02x}' for c in response)
                log.info(f"Baord serial number {sn}")
            return sn
        
        # communication path
        def setCommunicationPath(self, path:Union[int|str]) -> bool:
            '''
            Set the communication path to I2C (0), USB (1), or UART (2).  
            Once the new path is set, the board will reboot and the existing path will be disabled.  
            Wait >700ms for reboot before sending additional commands.  
            See Theia-motor-driver-instructions (available from the website https://theiatech.com/mcr) for more information 
            about wiring and power for the different paths.  
            ### input: 
            - path: new path as integer or string (all caps)
            ### return: 
            [success]
            '''
            newPath = 1
            if isinstance(path, str):
                if path in {'uart', 'UART'}:
                    newPath = 2
                elif path in {'i2c', 'I2C'}:
                    newPath = 0
                elif path in {'usb', 'USB'}:
                    newPath = 1
                else:
                    log.error(f'New comm path ({path}) not recognized.  Choose I2C, USB, or UART')
                    return False
            else:
                if newPath > 2 or newPath < 0:
                    log.error('New comm path index out of range (0~2)')
                    return False
                newPath = path

            # set the new path
            cmd = bytearray(3)
            cmd[0] = 0x6B
            cmd[1] = newPath
            cmd[2] = 0x0D
            self.MCRSendCmd(cmd)
            log.info(f'New comm path set ({newPath})')
            return True

        #------internal commands---------------------------------------------------------------------------------
        # MCRMotorInit
        def MCRMotorInit(self, id:int, steps:int, pi:int, speedRange:int, DCMotorType:bool=False) -> bool:
            '''
            Initialize motor. 
            Initialize steps and speeds.  No motor movement is done.  See the motor control specification document
            for more information.  
            Initialization byte array: 
            [setup cmd, motor ID, motor type, left stop, right stop, steps (2), min speed (2), max speed (2), CR]
            ### input: 
            - id: motor ID
            - steps: max number of steps
            - pi: pi step number
            - speedRange: 0: slow speed range 10-200 pps (iris) | 1: fast speed range 100-1500 pps (focus/zoom)
            - DCMotorType (optional: False): set if the motor is a DC motor otherwise (False) it is a stepper
            ### return: 
            [success]
            '''
            steps = int(steps)
            pi = int(pi)

            cmd = bytearray(12)
            cmd[0] = 0x63
            cmd[1] = id
            cmd[2] = 0x01 if DCMotorType else 0x00
            cmd[3] = 0
            cmd[4] = 0
            cmd[11] = 0x0D

            if speedRange == 1:
                # focus/zoom motor speed range.  min (100) and max (1500) speeds
                cmd[7] = 0
                cmd[8] = 0x64
                cmd[9] = 0x05
                cmd[10] = 0xDC
            else:
                # iris motor speed range.  min (10) and max (200) speeds
                cmd[7] = 0
                cmd[8] = 0x0A
                cmd[9] = 0
                cmd[10] = 0xC8
            
            if (id == MCR_FOCUS_MOTOR_ID) or (id == MCR_ZOOM_MOTOR_ID):
                # check for stop positions: wide/far at high motor steps. wide/far are at low motor steps
                # check if PI is closer to low (0) or high (max) side
                if (steps - pi) < pi:
                    # use left stop (max)
                    cmd[3] = 1
                else:
                    # use right stop (0)
                    cmd[4] = 1

            # max steps
            # convert integers to bytes and copy
            bSteps = int(steps).to_bytes(2, 'big')
            cmd[5] = bSteps[0]
            cmd[6] = bSteps[1]

            # send the command
            response = bytearray(12)
            response = self.MCRSendCmd(cmd)

            success = True
            if response[1] == 0x01:
                log.error("Error: init motor response")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                success = False
            return success
        
        # MCRMove
        def MCRMove(self, id:int, steps:int, speed:int, acceleration:int=0) -> bool:
            '''
            Send the move command byte string. 
            Move the motor by a number of steps
            (NOTE: Iris step direction for MCR is reversed (0x66(+) is iris closed) so invert step direction before moving)
            Command byte array: 
            [move cmd, motor ID, steps (2), start, speed (2), CR]
            ### input: 
            - id: motor id (focus/zoom/iris/IRC)
            - steps: number of steps to move
            - speed: (pps) motor speed
            - acceleration (optional: 0): motor start/stop acceleration steps (See the motor control documentation to see if this acceleration is supported in the firmware)
            ### return: 
            [success]
            '''
            steps = int(steps)
            speed = int(speed)

            cmd = bytearray(8)
            cmd[1] = id
            cmd[4] = 1
            cmd[7] = 0x0D

            if id is MCR_IRIS_MOTOR_ID:
                # reverse iris step direction
                if steps >= 0:
                    # move negative towards open
                    cmd[0] = 0x62
                else:
                    # move positive towards closed
                    cmd[0] = 0x66
                    steps = abs(steps)
            else:
                if steps >= 0:
                    # move positive towards far/wide
                    cmd[0] = 0x66
                else:
                    # move negative towards near/tele
                    cmd[0] = 0x62
                    steps = abs(steps)
            
            # steps and speed
            # convert integers to bytes and copy
            bSteps = int(steps).to_bytes(2, 'big')
            cmd[2] = bSteps[0]
            cmd[3] = bSteps[1]
            
            bSpeed = int(speed).to_bytes(2, 'big')
            cmd[5] = bSpeed[0]
            cmd[6] = bSpeed[1]

            # send the command
            waitTime = int((steps * 1050) / speed)  # add 5% to accont for slightly slow speed compared to set speed (noticed error on 8000 steps)
            response = bytearray(12)
            response = self.MCRSendCmd(cmd, waitTime)

            success = True
            if response[1] != 0x00:
                log.error("Error: move motor response")
                err.saveError(err.ERR_MOVE_TIMEOUT, err.MOD_MCR, err.errLine())
                success = False
            return success
        
        # MCRReadConfig
        def MCRReadMotorSetup(self, id:int) -> tuple:
            '''
            Read the configuration of the motor.  The configuration includes: 
            - motor type: stepper (0) or DC (1)
            - use left stop: True/False
            - use right stop: True/False
            - max steps: maximum number of steps in the range of the motor
            - min speed: (pps) minimum speed
            - max speed: (pps) maximum speed
            ### input: 
            - id: motor id (focus/zoom/iris/IRC)
            ### return: 
            [
                success: True if MCR returned a valid response |
                motor type: stepper (0) or DC (1) | 
                use left stop: True/False | 
                use right stop: True/False | 
                max steps: maximum number of steps | 
                min speed: minimum speed | 
                max speed: maximum speed
            ]
            '''
            if id not in [MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID, MCR_IRIS_MOTOR_ID, MCR_IRC_MOTOR_ID]:
                log.error("Error: Motor ID not recognized")
                err.saveError(err.ERR_RANGE, err.MOD_MCR, err.errLine())
                return False, None, None, None, None, None, None
            
            command = bytearray(3)
            command[0] = 0x67
            command[1] = id
            command[2] = 0x0D
            response = self.MCRSendCmd(command)

            # Check against invalid motor id
            # [0x67, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x0D]
            if response[1] == 0xFF:
                log.error("Error: controller responded with invalid motor id")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                return False, None, None, None, None, None, None

            try:
                # Parse the response
                (
                    commandId,
                    motorId,
                    motorType,
                    useLeftStop,
                    useRightStop,
                    maxStepsMsb,
                    maxStepsLsb,
                    minSpeedMsb,
                    minSpeedLsb,
                    maxSpeedMsb,
                    maxSpeedLsb,
                    _,  # carriage return
                ) = response
            except ValueError as e:
                log.error(f"Failed to parse response: response=[{', '.join([f'{int(x):02X}' for x in response])}] ({e})")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                return False
            
            # combine the MSB and LSB bytes to get values
            maxSteps = (maxStepsMsb << 8) | maxStepsLsb
            minSpeed = (minSpeedMsb << 8) | minSpeedLsb
            maxSpeed = (maxSpeedMsb << 8) | maxSpeedLsb
            
            return True, int(motorType), bool(useLeftStop), bool(useRightStop), int(maxSteps), int(minSpeed), int(maxSpeed)

        # MCRWriteConfig
        def MCRWriteMotorSetup(self, id:int, useLeftStop:bool, useRightStop:bool, maxSteps:int, minSpeed:int, maxSpeed:int) -> bool:
            '''
            Write the configuration of the motor.
            ### input: 
            - id: motor id (focus/zoom/iris/IRC)
            - useLeftStop: True/False (wide/far stops)
            - useRightStop: True/False (tele/near stops)
            - maxSteps: maximum number of steps
            - minSpeed: minimum speed
            - maxSpeed: maximum speed
            ### return: 
            [True] if MCR returned a valid response
            '''
            # check the motor ID
            if id in [MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID, MCR_IRIS_MOTOR_ID]:
                motorType = 0x00  # Stepper motor
            elif id in [MCR_IRC_MOTOR_ID]:
                motorType = 0x01
            else:
                log.error("Error: Motor ID not recognized")
                err.saveError(err.ERR_RANGE, err.MOD_MCR, err.errLine())
                return False

            # structure the command
            command = bytearray(12)
            command[0] = 0x63
            command[1] = id
            command[2] = motorType
            command[3] = int(useLeftStop)
            command[4] = int(useRightStop)
            command[5] = (maxSteps >> 8) & 0xFF
            command[6] = maxSteps & 0xFF
            command[7] = (minSpeed >> 8) & 0xFF
            command[8] = minSpeed & 0xFF
            command[9] = (maxSpeed >> 8) & 0xFF
            command[10] = maxSpeed & 0xFF
            command[11] = 0x0D
            response = self.MCRSendCmd(command)

            # check the response
            if response[1] != 0x00:
                log.error("Error: init motor response")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                return False
            return True

        # MCRRegardLimits
        def MCRRegardLimits(self, id:int, state:bool=True, PISide:int=1) -> bool:
            '''
            Set the regard limits flag in the board software.  
            Set the focus and zoom limit switches to true/false.  If they are set the motor will not drive
            passed the limit however there may be some cases where the motor must go past the limit to reach 
            the desired point.  The limit switch should be turned off but beware of backlash when driving past 
            the limit switch.  
            ### input: 
            - id: motor id (focus/zoom)
            - state (optional: True): set limits
            - PISide (optional: high): low (-1) or high (1) side PI step
            ### return: 
            [True] if MCR returned a valid response
            '''
            if (id != MCR_FOCUS_MOTOR_ID) and (id != MCR_ZOOM_MOTOR_ID):
                log.error('Motor has no limit switch')
                return False
            
            # read the current motor state so step and speed ranges don't have to be changed.  
            getCmd = bytearray(3)
            getCmd[0] = 0x67
            getCmd[1] = id
            getCmd[2] = 0x0D

            res = bytearray(12)
            res = self.MCRSendCmd(getCmd)
            setCmd = bytearray(12)
            for i, b in enumerate(res):
                setCmd[i] = b
            setCmd[0] = 0x63
            setCmd[3] = 0
            setCmd[4] = 0

            if state:
                if PISide == 1:
                    # use left stop (max)
                    setCmd[3] = 1
                else:
                    # use right stop (0)
                    setCmd[4] = 1
            
            # send the modified command
            response = bytearray(12)
            response = self.MCRSendCmd(setCmd)

            if response[1] != 0x00:
                log.error("Error: init motor response")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                return False
            return True

        # MCRSendCmd
        def MCRSendCmd(self, cmd, waitTime:int=10):
            '''
            Send the command through the com port over USB connection to the board.  This function should be 
            chnged for UART or I2C communication protocol instead of USB.  
            Send the byte string to the MCR-IQ board.  
            ### input: 
            - cmd: byte string to send
            - waitTime: (ms) wait before checking for a response
            ### return: 
            [return byte string from MCR]
            '''
            debugCheck = False   # set True to print send/receive byte strings
            # send the string
            if debugCheck: log.debug("   -> {}".format(":".join("{:02x}".format(c) for c in cmd)))
            self.serialPort.write(cmd)

            # wait for a response (wait first then check for the response)
            response = bytearray(12)
            readSuccess = False
            startTime = time.time() * 1000
            while(time.time() * 1000 - waitTime < startTime): 
                # wait until finished moving (waitTime milliseconds) or until PI triggers serial port buffer response
                if self.serialPort.in_waiting > 0: break
                time.sleep(0.1)

            # read the response
            startTime = time.time() * 1000
            while (time.time() * 1000 - RESPONSE_READ_TIME < startTime): 
                # Wait until there is data waiting in the serial buffer
                if (self.serialPort.in_waiting > 0):
                    # Read data out of the buffer until a carraige return / new line is found or until 12 bytes are read
                    response = self.serialPort.readline()
                    readSuccess = True
                    break
                else:
                    time.sleep(0.1)

            if not readSuccess:
                # timed out
                response[0] = 0x74
                response[1] = 0x01      # not successful
                response[2] = 0x0D
                log.warning("MCR send command timed out without response")

            # return response
            if debugCheck: log.debug("  <- None") if response == None else log.debug("   <- {}".format(":".join("{:02x}".format(c) for c in response)))
            return response