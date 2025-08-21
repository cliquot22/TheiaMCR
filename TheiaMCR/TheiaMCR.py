# Theia Technologies MCR control module
# This module allows the user to control the MCR600 series lens control boards.  There are functions to
# initialize the board and motors and to control the movements (relative, absolute, etc).  
# The board must be initizlized first using the MCRControl __init__ function.  Then the motors must
# all be initialize with their steps and limit positions.  The init commands will create instances
# of the motor class for each motor.  
# See more information at https://github.com/cliquot22/TheiaMCR  
#
# (c) 2023-2025 Theia Technologies
# www.TheiaTech.com
# BSD 3-clause license applies

import serial
import time
import TheiaMCR.errList as err
import logging
from os import path
import TheiaMCR.rotatingLogFiles as rotLogFiles
import sys

# create a logger instance for this module
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# internal constants used across the classes in this module.  
MCR_REVISION = 'v.3.3.0'

RESPONSE_READ_TIME = 500                # (ms) max time for the MCR to post a response in the buffer
MCR_FOCUS_MOTOR_ID = 0x01               # motor ID's as specified in the motor control documentation
MCR_ZOOM_MOTOR_ID = 0x02
MCR_IRIS_MOTOR_ID = 0x03
MCR_IRC_MOTOR_ID = 0x04
MCR_FOCUS_ZOOM_MOTORS_IDS = [MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID]
MCR_STEPPER_MOTORS_IDS = [MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID, MCR_IRIS_MOTOR_ID]
MCR_FZ_DEFAULT_SPEED = 1200           # (pps) default focus/zoom motor speeds
MCR_FZ_HOME_SPEED = 1200              # (pps) speed to travel to home PI position
MCR_FZ_APPROACH_SPEED = 500           # (pps) slow home approach speed for PI position
MCR_IRIS_DEFAULT_SPEED = 100          # (pps) default iris motor speed
MCR_IRC_DEFAULT_SPEED = 1000          # (pps) IRC default speed = 1ms/pulse
MCR_IRC_SWITCH_TIME = 50              # (ms) switch time for IRC
MCR_BACKLASH_OVERSHOOT = 60           # used to remove lens backlash, this should exceed lens maximum backlash amount
MCR_HARDSTOP_TOLERANCE = 200          # additional move amount to be sure to pass home position from hard stop (works best to prevent motor reversing if >100 steps)
MCR_MOVE_REST_TIME = 0.010            # (s) rest time between moves

##### unhandled exception handlier ###############################
def unhandledException(exc_type, exc_value, exc_traceback):
    '''
    Handle unhandled exceptions in the MCRControl module.  This will log the exception to the console and to the log file.
    This function is globally called with the sys.excepthook function.  Any unhandled exception will be printed in the log file and 
    available to higher programs.  
    '''
    if hasattr(MCRControl, 'MCRInitialized') and MCRControl.MCRInitialized:
        # check if MCRControl has been initizlized
        MCRControl.log.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    else:
        # Fallback logging if MCRControl is not initialized
        log.error("Unhandled exception occurred before MCRControl initialization:", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = unhandledException

##### wrapper functions to check for initialization ##############
def MCRInitFailed():
    '''
    This class is used to handle the case when MCRControl is not initialized.
    It provides a way to prevent crashes when trying to access methods or attributes
    of MCRControl when it is not initialized.
    '''
    def __getattr__(self, name):
        def method(*args, **kwargs):
            MCRControl.log.error(f'{name} cannot be executed because MCRBoard is not initialized.')
            err.saveError(err.ERR_NOT_INIT, err.MOD_MCR, err.errLine())
            return err.ERR_NOT_INIT
        return method
    
#####################################################################################
# MCRControl class
class MCRControl():
    # pseudo-constants
    communicationDebugLevel = False      # set to True to print debug messages to the console (not recommended for production use)
    log = None                          # logger

    # class variables
    MCRInitialized = False
    _instances = {}  # dictionary to store instances by serialPortName

    def __new__(cls, serialPortName, *args, **kwargs):
        '''
        Called when a new instance of the class is created.  This function will check if an instance already exists for the given serial port name.
        '''
        if serialPortName in cls._instances:
            return cls._instances[serialPortName]
        instance = super(MCRControl, cls).__new__(cls)
        cls._instances[serialPortName] = instance
        return instance

    # MCRInit
    def __init__(self, serialPortName:str, moduleDebugLevel:bool=False, communicationDebugLevel:bool=False, logFiles:bool=True):
        '''
        This class is used for interacting with the Theia MCR motor control boards. 
        Initialize the MCR board (this class) before any commands can be sent.  
        Successful initialization is confirmed by receiving the board firmware version from the board.  
        This can be checked by referencing the MCRControl.MCRInitialized variable.   
        Motor initialization (focusInit, zoomInit, irisInit) must be called separately for each motor. 

        This is the top level class for all interactions with the MCR600 series boards
        ### input: 
        - serialPortName: the serial port name of the board (e.g. "com21" or "/dev/ttyAMA0").   
        - moduleDebugLevel (optional boolean: False): Set true to set the level to DEBUG for the console stream instead of the default of INFO
        - communicationDebugLevel (optional boolean: False): Set true to print the serial port communication to the console (and all debug level logs).  This is not recommended for production use.  
        - logFiles (optional boolean: True): Set true to create log files for the MCR board.  The log files will be created in the user directory.  
        ### Public functions: 
        - __init__(self, com:str, moduleDebugLevel:bool=False, communicationDebugLevel:bool=False, logFiles:bool=True)
        - focusInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool
        - zoomInit(self, steps:int, pi:int, move:bool=True, accel:int=0) -> bool
        - irisInit(self, steps:int, move:bool=True) -> bool
        - IRCInit(self) -> bool
        - close(self)   # call this function to close the serial port and release the resources
        - checkBoardCommunication(self) -> bool   # confirm the com port is still open and communication with the board is possible
        ### class variables
        - MCRInitialized: set to True when the class is successfully initialized (with regard to logging)
        ### instance variables  
        - boardInitialized: set to True with this instance of the class (this board) is initialized and com port is open
        - boardCommunicationState: set to True (in MCRCom._sendCmd()) when the board communication is successful
        - boardCommunicationRestarts: counts the number of times communication with the board has been restarted
        ### Sub-classes: 
        - motor
        - controllerClass
        - MCRCom

        (c)2023-2025 Theia Technologies
        www.TheiaTech.com
        '''
        if self.MCRInitialized:
            MCRControl.log.warning(f'MCRControl already initialized for {serialPortName}')
            return
        
        self.boardInitialized = False
        self.boardCommunicationState = False
        self.boardCommunicationRestarts = 0
        self.serialPort = None
        self.serialPortName = serialPortName
        
        MCRControl.communicationDebugLevel = communicationDebugLevel
        if communicationDebugLevel: moduleDebugLevel = True
        self._initLogging(moduleDebugLevel, logFiles, serialPortName) 
        MCRControl.MCRInitialized = True

        success = 0
        # open the com port
        self.com = self.MCRCom(parent=self, serialPortName=serialPortName)
        success = self.com.initialized
        self.serialPort = self.com.serialPort

        # set the initialized flag to allow readFWRevision to be called
        if success >= 0:
            self.boardInitialized = True if self.com.initialized >= 0 else False
            self.MCRBoard = self.controllerClass(parent=self)
            # send a test command to the board to read FW version
            response = self.MCRBoard.readFWRevision()
            if response == None or int(response.rsplit('.', -1)[0]) < 5:
                MCRControl.log.error("Error: No resonse received from MCR controller")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                success = err.ERR_NO_COMMUNICATION
            else:
                self.boardCommunicationState = True
        self.boardInitialized = True if success >= 0 else False        # set initialization state

        # ultimate success
        if success >= 0:
            self.focus = None 
            self.zoom = None
            self.iris = None
        else:
            self.focus = MCRInitFailed()
            self.zoom = MCRInitFailed()
            self.iris = MCRInitFailed()
            self.MCRBoard = MCRInitFailed()

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
        [True | (False, error int)] if motor initialization was successful or not
        '''
        if not self.boardInitialized: 
            MCRControl.log.warning(f'focusInit can\'t be called because board isn\'t initialized')
            return False
        
        MCRControl.log.debug(f'_init,{MCR_FOCUS_MOTOR_ID}')
        self.focus = self.motor(self, MCR_FOCUS_MOTOR_ID, steps, pi, move, accel)
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
        [True | (False, error int)] if motor initialization was successful or not
        '''
        if not self.boardInitialized: 
            MCRControl.log.warning(f'zoomInit can\'t be called because board isn\'t initialized')
            return False
        
        MCRControl.log.debug(f'_init,{MCR_ZOOM_MOTOR_ID}')
        self.zoom = self.motor(self, MCR_ZOOM_MOTOR_ID, steps, pi, move, accel)
        return self.zoom.initialized
    
    def irisInit(self, steps:int, move:bool=True) -> bool:
        '''
        Initialize the parameters of the motor.  This must be called after the board is initialized.  
        ### input: 
        - steps: maximum number of steps
        - move: (optional, True) move motor to home position or (False) initialize without moving. 
        ### return: 
        [True | (False, error int)] if motor initialization was successful or not
        '''
        if not self.boardInitialized: 
            MCRControl.log.warning(f'irisInit can\'t be called because board isn\'t initialized')
            return False
        
        MCRControl.log.debug(f'_init,{MCR_IRIS_MOTOR_ID}')
        self.iris = self.motor(self, MCR_IRIS_MOTOR_ID, steps, pi=0, move=move, accel=0)
        return self.iris.initialized

    # IRCInit
    def IRCInit(self) -> bool:
        '''
        Initialize the parameters of the IRC motor.  
        For the IRC switch motor: maximum 1000 steps allows 1 second activation time (at speed 1000pps).  The activation
        time is set by the number of steps (1 step = 1 ms).  See the motor control docuemtation for more info.  
        ### return: 
        [True | (False, error int)] if motor initialization was successful or not
        '''
        if not self.boardInitialized: 
            MCRControl.log.warning(f'IRCInit can\'t be called because board isn\'t initialized')
            return False
        
        MCRControl.log.debug(f'_init,{MCR_IRC_MOTOR_ID}')
        self.IRC = self.motor(self, MCR_IRC_MOTOR_ID, pi=0, steps=1000, move=False)
        return self.IRC.initialized
    
    # close log files
    def closeLogFiles(self):
        '''
        This function closes the log files for TheiaMCR and releases the resources.  
        There is no function to re-open log files.  Close and recreate this class.  
        '''
        MCRControl.log.debug('_closeLogFiles')
        if self.fileLogHandler:
            self.fileLogHandler.close()
            MCRControl.log.info('TheiaMCR logging file closed')
    
    # close instance
    def close(self):
        '''
        Close the MCR board and release the serial port and other resources.
        '''
        MCRControl.log.debug('_close (exit)')
        if self.com.initialized:
            self.serialPort.close()
            self.serialPort = None
            self.com.initialized = False

        if self.MCRBoard: 
            self.MCRBoard = None
        if self.focus: 
            self.focus = None
        if self.zoom: 
            self.zoom = None
        if self.iris: 
            self.iris = None

        if self.fileLogHandler:
            self.fileLogHandler.close()
            self.fileLogHandler = None
        if self.consoleLogHandler: 
            self.consoleLogHandler.close()
            self.consoleLogHandler = None

    # check and reopen board communication via serial port
    def checkBoardCommunication(self) -> bool:
        '''
        Check the communication with the MCR board.  If the communication is not successful, 
        attempt to restart the serial port.  Check communication again and return the result.  
        ### return:  
        - True if the communication is successful, False otherwise.
        '''
        boardCommunication = self.com._verifyCommunication()
        return boardCommunication
    
    ############ internal functions ##############################################################
    # set up logging 
    def _initLogging(self, consoleLog:bool, fileLog:bool, serialPortName:str=''):
        '''
        Set up the console log and file logging as required. 
        ### input:  
        - consoleLog: set true to see DEBUG level values in the console, otherwise it will be set to INFO level.  
        - fileLog: set true to save logs to a file. 
        - serialPortName: (optional: '') the serial port name for the log file
        '''
        # set up logging
        self.fileLogHandler = None
        self.consoleLogHandler = None
        MCRControl.log = logging.getLogger(__name__+'.MCRControl')

        if fileLog:
            # Set up log files.  Remove the NullHandler if present (in case logging was not set up in the main program)
            nullHandlers = [h for h in MCRControl.log.handlers if isinstance(h, logging.NullHandler)]
            for handler in nullHandlers:
                MCRControl.log.removeHandler(handler)
            self.fileLogHandler = rotLogFiles.rotatingLogFiles(MCRControl.log, nameKey=serialPortName)
            MCRControl.log.info(f'Log file path {path.split(self.fileLogHandler.filenames[0])[0]}')

        self.consoleLogHandler = logging.StreamHandler()
        self.consoleLogHandler.setLevel(logging.DEBUG) if consoleLog else self.consoleLogHandler.setLevel(logging.INFO)

        # Copy the formatter from the root logger's StreamHandler
        for handler in logging.root.handlers:
            if isinstance(handler, logging.StreamHandler):
                self.consoleLogHandler.setFormatter(handler.formatter)
                break  # Stop after finding the first StreamHandler
        MCRControl.log.addHandler(self.consoleLogHandler)
        # stop the log messages from propogating to additional stream handlers
        MCRControl.log.propagate = False

        MCRControl.log.info(f'TheiaMCR module version {MCR_REVISION}')
        MCRControl.log.debug('TheiaMCR module logging level: DEBUG')

    
    ############## Depricated functions (moved from controllerClass to motor class in v.3.0.0) ###########
    # IRCState
    def IRCState(self, state:int) -> int:
        ''' Depricated function TheiaMCR.MCRControl.IRCState, use motor.IRCState instead. '''
        MCRControl.log.warning('Depricated TheiaMCR.IRCState, use motor.state instead')
        return self.IRC.state(state)

    ######################################################################################################
    # Motor definition class
    class motor():
        # initialize the parameters of the motor
        def __init__(self, parent, motorID:bytes, steps:int, pi:int, move:bool=True, accel:int=0):
            '''
            The class is used for the focus, zoom, and iris motors.  The only difference between these motors are speeds and number of steps.  
            ### Public functions: 
            - __init__(self, motorID:bytes, steps:int, pi:int, move:bool=True, accel:int=0, DCMotorType:bool=False)
            - home(self) -> int
            - moveAbs(self, step:int) -> int
            - moveRel(self, steps:int, correctForBL:bool=True) -> int
            - state(self, state:int) -> int   (only applicable to IRC)
            - setMotorSpeed(self, speed) -> int
            - setRespectLimits(self, state:bool)
            - readMotorSetup(self) -> Tuple[bool, int, bool, bool, int, int, int, int]
            - writeMotorSetup(self, useWideFarStop:bool, useTeleNearStop:bool, maxSteps:int, minSpeed:int, maxSpeed:int) -> bool
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
            ### instance variables
            - initialized
            - currentStep
            - currentSpeed
            - homingSpeed
            - PIStep (step position of the photo interrupter limit switch)
            - maxSteps
            - respectLimits (set True to prevent motor from exceeding limits)
            ### Private functions:
            - checkLimits(self, steps:int, limitStep:bool=False) -> int
            '''
            self.parent = parent
            self.com = parent.MCRCom(parent)
            self.motorID = motorID
            self.PIStep = pi
            self.maxSteps = steps
            self.respectLimits = True
            # set acceleration
            self.acceleration = accel << 3 | 0x01

            # set PI side
            if (steps - pi) < pi:
                self.PISide = 1
            else:
                self.PISide = -1

            # set the motor speed range
            speedRange = 0
            if self.motorID in MCR_FOCUS_ZOOM_MOTORS_IDS:
                self.currentSpeed = MCR_FZ_DEFAULT_SPEED
                self.homingSpeed = MCR_FZ_HOME_SPEED
                speedRange = 1
            elif self.motorID == MCR_IRIS_MOTOR_ID:
                self.currentSpeed = MCR_IRIS_DEFAULT_SPEED
            else:
                self.currentSpeed = MCR_IRC_DEFAULT_SPEED

            # initialize the motor control board instance for sending the commands
            self.MCRBoard = MCRControl.controllerClass(parent=self.parent)
            success = self._motorInit(pi=self.PIStep, steps=self.maxSteps, speedRange=speedRange)
            if not success:
                MCRControl.log.error('Motor not initialized')
                err.saveError(err.ERR_NOT_INIT, err.MOD_MCR, err.errLine())
            else:
                self.currentStep = 0
                error = err.ERR_OK
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
                err_bad_move: (PI was nto set or triggered (call motorInit first)) |  
                err_not_supported: (function not supported by this motor)
            ]
            '''
            MCRControl.log.debug(f'_home,{self.motorID}')
            if self.motorID not in MCR_STEPPER_MOTORS_IDS: 
                MCRControl.log.warning(f'"home" function not supported by motor {self.motorID}')
                return err.ERR_NOT_SUPPORTED

            # store current state of limit switches
            setIgnoreLimitsToFalse = False
            if not self.respectLimits:
                # reset respectLimits back to false after home
                setIgnoreLimitsToFalse = True
                self.setRespectLimits(True)
            
            # move the motor to expected PI position (110% of max steps)
            homeSpeed = self.homingSpeed if self.motorID in MCR_FOCUS_ZOOM_MOTORS_IDS else MCR_IRIS_DEFAULT_SPEED
            homeApproachSpeed = MCR_FZ_APPROACH_SPEED if self.motorID in MCR_FOCUS_ZOOM_MOTORS_IDS else MCR_IRIS_DEFAULT_SPEED
            success = self._motorMove(steps=(self.maxSteps * 1.1) * self.PISide, speed=max(self.currentSpeed, homeSpeed), acceleration=self.acceleration)
            if self.motorID == 0x01 or self.motorID == 0x02:
                # confirm the motor is at the PI and not past the PI position, move the difference between max steps and PI position + 40 steps over the expected (max - PIStep) to be sure since the physical max step is variable.  
                piCheckSteps = (self.PIStep - self.maxSteps) if self.PISide == 1 else self.PIStep
                time.sleep(MCR_MOVE_REST_TIME)
                # move away from PI at full speed
                self._motorMove(steps=(piCheckSteps - self.PISide * MCR_HARDSTOP_TOLERANCE), speed=max(self.currentSpeed, homeSpeed), acceleration=self.acceleration)
                time.sleep(MCR_MOVE_REST_TIME)
                # move back, towards PI at full speed but not all the way
                self._motorMove(steps=-piCheckSteps + self.PISide * (MCR_HARDSTOP_TOLERANCE - 50), speed=max(self.currentSpeed, homeSpeed), acceleration=self.acceleration)
                # slow down and hit PI at slower speed
                success = self._motorMove(steps=self.PISide * 100, speed=homeApproachSpeed, acceleration=self.acceleration)

            # reset the respect limit state
            if setIgnoreLimitsToFalse: self.setRespectLimits(False)
            if success:
                self.currentStep = self.PIStep
            else:
                MCRControl.log.error(f"Error: Motor 0x{self.motorID:02X} move error")
                err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
                return err.ERR_BAD_MOVE
            MCRControl.log.debug(f'_finalStep,{self.motorID},,{self.currentStep}')
            return err.ERR_OK
        
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
                err_param: if there is an input error |  
                err_not_supported: (function not supported by this motor)
            ]
            '''
            MCRControl.log.debug(f'_moveAbs,{self.motorID},{step}')
            if self.motorID not in MCR_STEPPER_MOTORS_IDS: 
                MCRControl.log.warning(f'"moveAbs" function not supported by motor {self.motorID}')
                return err.ERR_NOT_SUPPORTED

            if step < 0:
                MCRControl.log.warning("Warning: target motor step < 0")

            # move to PI position
            error = self.home()
            if error != 0:
                MCRControl.log.error("Error: focus home error")
                err.saveError(error, err.MOD_MCR, err.errLine())
                return error

            # move to absolute position
            steps = step - self.PIStep
            error = self.moveRel(steps)
            if error != 0:
                # propogate error
                err.saveError(error, err.MOD_MCR, err.errLine())
                return error
            MCRControl.log.debug(f'_finalStep,{self.motorID},,{self.currentStep}')
            return err.ERR_OK
        
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
                err_bad_move: if there is a move error  |  
                err_not_supported: (function not supported by this motor)
            ]
            '''
            MCRControl.log.debug(f'_moveRel,{self.motorID},{steps}')
            if self.motorID not in MCR_STEPPER_MOTORS_IDS: 
                MCRControl.log.warning(f'"moveRel" function not supported by motor {self.motorID}')
                return err.ERR_NOT_SUPPORTED

            if steps == 0:
                return err.ERR_OK

            # check for limits
            limit, steps = self._checkLimits(steps, self.respectLimits)
            if self.respectLimits and (limit != 0):
                MCRControl.log.warning(f'Limiting focus relative steps to {steps}')

            # move the motor
            success = False
            blCorrection = MCR_BACKLASH_OVERSHOOT
            if correctForBL and (steps * self.PISide > 0):
                # moving towards PI, add backlash adjustment and keep any moves within PI limit or min/max limits
                blCorrection = max(0,min(MCR_BACKLASH_OVERSHOOT, self.PIStep * ((self.PIStep if self.respectLimits else (self.maxSteps if self.PIStep > 0 else 0)) - (steps + self.currentStep))))

                success = self._motorMove(steps + self.PISide * blCorrection, self.currentSpeed, self.acceleration)
                if blCorrection > 0: 
                    # move back by the BL correction amount
                    time.sleep(MCR_MOVE_REST_TIME)
                    success = self._motorMove(-self.PISide * blCorrection, self.currentSpeed, self.acceleration)
            else:
                # no need for backlash adjustment
                success = self._motorMove(steps, self.currentSpeed, self.acceleration)
                
            self.currentStep += steps
            if not success:
                err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
                return err.ERR_BAD_MOVE
            MCRControl.log.debug(f'_finalStep,{self.motorID},,{self.currentStep}')
            return err.ERR_OK
        
        # IRCState
        def state(self, state:int) -> int:
            '''
            Set the IRC state to either visible or clear filter (or other options depending on the lens model)
            ### input: state: [  
            1: Visible (IR blocking) filter 1 |  
            2: clear filter 2  
            ]
            ### return: 
            [new state (1 | 2) | error code] (error code <0)
            '''
            MCRControl.log.debug(f'_state,{self.motorID},{state}')
            if self.motorID != MCR_IRC_MOTOR_ID: 
                MCRControl.log.warning(f'"state" function not supported by motor {self.motorID}')
                return err.ERR_NOT_SUPPORTED

            sw = MCR_IRC_SWITCH_TIME  ## move in positive direction
            if state == 1:
                sw *= -1                ## move in negative direction
            success = self._motorMove(steps=sw, speed=MCR_IRC_DEFAULT_SPEED)

            if not success: return err.ERR_BAD_MOVE
            return state
        
        # setRespectLimits
        def setRespectLimits(self, state:bool):
            '''
            Set the flag to stop motor moves at the PI limits or to continue past the limits.  In some cases
            the limits should be turned off to get to the target motor position.  
            ### input: 
            - state: set or remove the limit
            ### globals: 
            - set the respectLimits variable.  
            ### return:  
            [state (T/F) or None if motor doesn't have PI]
            '''
            if self.motorID not in MCR_FOCUS_ZOOM_MOTORS_IDS:
                MCRControl.log.info('No PI for this motor')
                return None
            
            MCRControl.log.info(f'PI limit for {"focus" if self.motorID == MCR_FOCUS_MOTOR_ID else "zoom"} set to {state}')
            self.respectLimits = state
            self._regardLimits(state, self.PISide)
            return self.respectLimits

        # setMotorSpeed
        def setMotorSpeed(self, speed) -> int:
            '''
            Set the motor speed.  This is not stored on the board (only in this module) but it should be in the speed range stored on the board EEPROM.  
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
                    MCRControl.log.warning(f'Requested speed {speed} is outside range 100-1500')
                    return err.ERR_RANGE
            elif self.motorID == MCR_IRIS_MOTOR_ID:
                if speed > 200 or speed < 10:
                    MCRControl.log.warning(f'Requested speed {speed} is outside range 10-200')
                    return err.ERR_RANGE
            self.currentSpeed = speed
            MCRControl.log.debug(f'_finalSpeed,{self.motorID},,{self.currentSpeed}')
            return err.ERR_OK

        # setHomingSpeed
        def setHomingSpeed(self, speed) -> int:
            '''
            Set the motor speed used when seaking the photointerrupter home position for focus/zoom motors.  This is not 
            applicable to the iris motor.  
            This is not stored on the board (only in this module) but it should be in the speed range stored on the board EEPROM.  
            ### input: 
            - speed: speed to set [pps]
            ### globals: 
            - set homingSpeed
            ### return: 
            [
                OK = 0 |
                err_range, out of acceptable range 
            ]
            '''
            if self.motorID in {MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID}:
                if speed > 1500 or speed < 100:
                    MCRControl.log.warning(f'Requested speed {speed} is outside range 100-1500')
                    return err.ERR_RANGE
            self.homingSpeed = speed
            MCRControl.log.debug(f'_homingSpeed,{self.motorID},,{self.homingSpeed}')
            return err.ERR_OK

        # read/write motor configurations to EEPROM
        # MCRReadConfig
        def readMotorSetup(self) -> tuple[bool, int, bool, bool, int, int, int, int]:
            '''
            Read the configuration of the motor.  The configuration includes: 
            - motor type: stepper (0) or DC (1)
            - use wide/far (left) stop: True/False
            - use tele/near (right) stop: True/False
            - max steps: maximum number of steps in the range of the motor
            - min speed: (pps) minimum speed
            - max speed: (pps) maximum speed
            ### return: 
            [
                success: True if MCR returned a valid response,
                motor type: stepper (0) | DC (1) | error code (<0) if success is False,
                use wide/far stop: True/False, 
                use tele/near stop: True/False, 
                max steps: maximum number of steps, 
                min speed: minimum speed, 
                max speed: maximum speed
                OK | error value
            ]
            '''            
            command = bytearray(3)
            command[0] = 0x67
            command[1] = self.motorID
            command[2] = 0x0D
            response = self.com._sendCmd(command)

            # Check against invalid motor id
            # [0x67, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x0D]
            if response[1] == 0xFF:
                MCRControl.log.error("Error: controller responded with invalid motor id")
                err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                return False, -1, False, False, -1, -1, -1, err.ERR_NO_COMMUNICATION

            try:
                # Parse the response
                (
                    commandId,
                    motorId,
                    motorType,
                    useWideFarStop,
                    useTeleNearStop,
                    maxStepsMsb,
                    maxStepsLsb,
                    minSpeedMsb,
                    minSpeedLsb,
                    maxSpeedMsb,
                    maxSpeedLsb,
                    _,  # carriage return
                ) = response
            except ValueError as e:
                MCRControl.log.error(f"Failed to parse read motor values response [{', '.join([f'{int(x):02X}' for x in response])}] ({e})")
                if self.parent.boardCommunicationState:
                    # no response or incorrect response from the board
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                    return False, -1, False, False, -1, -1, -1, err.ERR_NO_COMMUNICATION
                else:
                    # serial port communication is not initialized
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                    return False, -1, False, False, -1, -1, -1, err.ERR_SERIAL_PORT
            
            # combine the MSB and LSB bytes to get values
            maxSteps = (maxStepsMsb << 8) | maxStepsLsb
            minSpeed = (minSpeedMsb << 8) | minSpeedLsb
            maxSpeed = (maxSpeedMsb << 8) | maxSpeedLsb
            
            return True, int(motorType), bool(useWideFarStop), bool(useTeleNearStop), int(maxSteps), int(minSpeed), int(maxSpeed), err.ERR_OK

        # MCRWriteConfig
        def writeMotorSetup(self, useWideFarStop:bool, useTeleNearStop:bool, maxSteps:int, minSpeed:int, maxSpeed:int) -> bool:
            '''
            Write the configuration of the motor.  This is stored in the controller board memory for each motor and will
            persist over restart of the board.  
            ### input: 
            - useWideFarStop: True/False (left stop)
            - useTeleNearStop: True/False (right stop)
            - maxSteps: maximum number of steps
            - minSpeed: minimum speed
            - maxSpeed: maximum speed
            ### return: 
            [True] if MCR returned a valid response
            '''
            MCRControl.log.debug(f'_writeMotorSetup,{self.motorID},{useWideFarStop},{useTeleNearStop},{maxSteps},{minSpeed},{maxSpeed}')
            # check the motor type (stepper or DC)
            motorType = 0x01 if self.motorID == MCR_IRC_MOTOR_ID else 0x00

            # structure the command
            command = bytearray(12)
            command[0] = 0x63
            command[1] = self.motorID
            command[2] = motorType
            command[3] = int(useWideFarStop)
            command[4] = int(useTeleNearStop)
            command[5] = (maxSteps >> 8) & 0xFF
            command[6] = maxSteps & 0xFF
            command[7] = (minSpeed >> 8) & 0xFF
            command[8] = minSpeed & 0xFF
            command[9] = (maxSpeed >> 8) & 0xFF
            command[10] = maxSpeed & 0xFF
            command[11] = 0x0D
            response = self.com._sendCmd(command)

            # check the response
            if response[1] != 0x00:
                MCRControl.log.error("Error: Write motor values failed")
                if self.parent.boardCommunicationState:
                    # no response or incorrect response from the board
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    # serial port communication is not initialized
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                return False
            return True

        ############ internal functions ##############################################################
        # checkLimits
        def _checkLimits(self, steps:int, limitStep:bool=False) -> int:
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
                MCRControl.log.warning(f"Warn: steps exceeds PI {self.PIStep}")
                retVal = 1
            elif limitStep and (self.PISide < 0) and (self.currentStep + steps < self.PIStep):
                if limitStep:
                    retSteps = min(self.PIStep - self.currentStep, 0)
                MCRControl.log.warning(f"Warn: steps exceeds low PI {self.PIStep}")
                retVal = -1
            elif self.currentStep + steps > self.maxSteps:
                if limitStep:
                    retSteps = max(self.maxSteps - self.currentStep, 0)
                MCRControl.log.warning(f"Warn: steps exceeds maximum {self.maxSteps}")
                retVal = 2
            elif self.currentStep + steps < 0:
                if limitStep:
                    retSteps = min(-self.currentStep, 0)
                MCRControl.log.warning(f"Warn: steps exceeds minimum 0")
                retVal = -2
            return retVal, retSteps
        
        # MCRMotorInit
        def _motorInit(self, steps:int, pi:int, speedRange:int) -> bool:
            '''
            Initialize motor. 
            Initialize steps and speeds.  No motor movement is done.  See the motor control specification document
            for more information.  
            Initialization byte array: 
            [setup cmd, motor ID, motor type, left stop, right stop, steps (2), min speed (2), max speed (2), CR]
            ### input: 
            - steps: max number of steps
            - pi: pi step number
            - speedRange: 0: slow speed range 10-200 pps (iris) | 1: fast speed range 100-1500 pps (focus/zoom)
            ### return: 
            [success]
            '''
            steps = int(steps)
            pi = int(pi)
            motorType = 0x01 if self.motorID == MCR_IRC_MOTOR_ID else 0x00

            cmd = bytearray(12)
            cmd[0] = 0x63
            cmd[1] = self.motorID
            cmd[2] = motorType
            cmd[3] = 0
            cmd[4] = 0
            cmd[11] = 0x0D

            if speedRange == 1:
                # focus/zoom motor speed range.  min (100) and max (1500) speeds
                cmd[7] = 0
                cmd[8] = 0x64
                cmd[9] = 0x05
                cmd[10] = 0xDC
            elif speedRange == 2:
                # iris motor speed range.  min (10) and max (200) speeds
                cmd[7] = 0
                cmd[8] = 0x0A
                cmd[9] = 0
                cmd[10] = 0xC8
            else: 
                # IRC motor speed range.  min (10) and max (1000) speeds (in steps per second)
                cmd[7] = 0
                cmd[8] = 0x0A
                cmd[9] = 0x03
                cmd[10] = 0xE8
            
            if self.motorID in MCR_FOCUS_ZOOM_MOTORS_IDS:
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
            response = self.com._sendCmd(cmd)

            success = True
            if response[1] == 0x01:
                MCRControl.log.error("Error: Motor init failed")
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                success = False
            return success
        
        # MCRMove
        def _motorMove(self, steps:int, speed:int, acceleration:int=0) -> bool:
            '''
            Send the move command byte string. 
            Move the motor by a number of steps.  
            (NOTE: Iris step direction for MCR is reversed (0x66(+) is iris closed) so invert step direction before moving).  
            
            If the move failed, check self.parent.boardCommunicationState to see if the board is still connected.  
            If communication is still active, consider redoing the move command or reinitializing the motor.  

            Command byte array: 
            [move cmd, motor ID, steps (2), start, speed (2), CR]
            ### input: 
            - steps: number of steps to move
            - speed: (pps) motor speed
            - acceleration (optional: 0): motor start/stop acceleration steps (See the motor control documentation to see if this acceleration is supported in the firmware)
            ### return: 
            [success]
            '''
            steps = int(steps)
            speed = int(speed)

            cmd = bytearray(8)
            cmd[1] = self.motorID
            cmd[4] = 1
            cmd[7] = 0x0D

            if self.motorID is MCR_IRIS_MOTOR_ID:
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
            waitTime = int((steps / speed) * 1000 * 1.15)  # add 15% to accont for slightly slow speed compared to set speed (noticed error on 8000 steps)
            response = bytearray(12)
            response = self.com._sendCmd(cmd, waitTime)

            success = True
            if response[1] != 0x00:
                MCRControl.log.error("Error: move motor failed")

                # check the board is still connected and communication is possible.  
                MCRControl.log.warning('Rechecking MCR board communication...')
                boardCommunication = self.com._verifyCommunication()
                MCRControl.log.warning(f'...Communication with MCR board {"re-established" if boardCommunication else "failed"}')

                if not self.parent.boardCommunicationState:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                success = False

            return success

        # MCRRegardLimits
        def _regardLimits(self, state:bool=True, PISide:int=1) -> bool:
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
            if self.motorID not in {MCR_FOCUS_MOTOR_ID, MCR_ZOOM_MOTOR_ID}:
                MCRControl.log.info('Motor has no limit switch')
                return False
            
            # read the current motor state so step and speed ranges don't have to be changed.  
            getCmd = bytearray(3)
            getCmd[0] = 0x67
            getCmd[1] = self.motorID
            getCmd[2] = 0x0D

            res = bytearray(12)
            res = self.com._sendCmd(getCmd)
            if len(res) == 0: 
                # no response from board for current state
                MCRControl.log.warning("Warning: no response from MCR board")
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                return False
            # exctract the proper response if the variable res includes more than one response
            for i in range(len(res)):
                if res[i] == getCmd[0]:
                    res = res[i:i+12]
                    break
            if len(res) > 12: 
                MCRControl.log.warning("Warning: MCR board response too long ({})".format(":".join("{:02x}".format(c) for c in res)))
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                return False
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
            response = self.com._sendCmd(setCmd)

            if response[1] != 0x00:
                MCRControl.log.error("Error: write motor configuration failed")
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                return False
            return True


    ###################################################################################################
    # Controller board functions
    class controllerClass():
        # initialize the control board 
        def __init__(self, parent):
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
            self.parent = parent
            self.com = parent.MCRCom(parent)

        # ----------- board information --------------------
        # get the FW revision from the board
        def readFWRevision(self) -> str:
            '''
            Get FW revision on the board. 
            Replies with string value of the firmware revision response
            ### return: 
            [string representing the FW revision (ex. '5.3.1.0.0')]
            '''
            if not self.parent.boardInitialized: 
                MCRControl.log.warning(f'readFWRevision can\'t be called because board isn\'t initialized')
                return None

            response = ""
            cmd = bytearray(2)
            cmd[0] = 0x76
            cmd[1] = 0x0D
            response = self.com._sendCmd(cmd)
            fw = ''
            if response == None:
                MCRControl.log.error("Error: No resonse received from MCR controller")
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
            else:
                fw = (".".join("{:x}".format(c) for c in response))
                fw = fw[3:-2]
                MCRControl.log.info(f"FW revision: {fw}")
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
            if not self.parent.boardInitialized: 
                MCRControl.log.warning(f'readBoardSN can\'t be called because board isn\'t initialized')
                return None

            response = ""
            cmd = bytearray(2)
            cmd[0] = 0x79
            cmd[1] = 0x0D
            response = self.com._sendCmd(cmd)
            sn = ''
            if response == None:
                MCRControl.log.error("Error: No resonse received from MCR controller")
                if self.parent.boardCommunicationState:
                    err.saveError(err.ERR_NO_COMMUNICATION, err.MOD_MCR, err.errLine())
                else:
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
            else:
                sn = f'{response[1]:02x}{response[2]:02x}'
                sn = sn[:-1]
                sn += f'-{response[-4]:02x}{response[-3]:02x}{response[-2]:02x}'
                MCRControl.log.info(f"Baord serial number {sn}")
            return sn
        
        # communication path
        def setCommunicationPath(self, path:int|str) -> bool:
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
            if not self.parent.boardInitialized: 
                MCRControl.log.warning(f'setCommunicationPath can\'t be called because board isn\'t initialized')
                return False

            newPath = 1
            if isinstance(path, str):
                if path in {'uart', 'UART'}:
                    newPath = 2
                elif path in {'i2c', 'I2C'}:
                    newPath = 0
                elif path in {'usb', 'USB'}:
                    newPath = 1
                else:
                    MCRControl.log.error(f'New comm path ({path}) not recognized.  Choose I2C, USB, or UART')
                    return False
            else:
                if newPath > 2 or newPath < 0:
                    MCRControl.log.error('New comm path index out of range (0~2)')
                    return False
                newPath = path

            # set the new path
            cmd = bytearray(3)
            cmd[0] = 0x6B
            cmd[1] = newPath
            cmd[2] = 0x0D
            self.com._sendCmd(cmd)
            MCRControl.log.info(f'New comm path set ({newPath})')
            return True

        
        ################### Depricated functions (moved from controllerClass to motor class in v.3.0.0) ###########
        # MCRReadConfig
        def MCRReadMotorSetup(self, id:int) -> tuple[bool, int, bool, bool, int, int, int]:
            '''Depricated MCRReadMotorSetup, use motor class readMotorSetup instead'''
            MCRControl.log.warning('Depricated TheiaMCR.controllerClass.MCRReadMotorSetup, use motor.readMotorSetup instead')
            if id == MCR_FOCUS_MOTOR_ID: retVal = MCRControl.focus.readMotorSetup()
            elif id == MCR_ZOOM_MOTOR_ID: retVal = MCRControl.zoom.readMotorSetup()
            elif id == MCR_IRIS_MOTOR_ID: retVal = MCRControl.iris.readMotorSetup()
            else: retVal = [False, -1, False, False, -1, -1, -1, -1]
            return retVal[:-1]  # return all but the last element (OK) to match the old function signature

        # MCRWriteConfig
        def MCRWriteMotorSetup(self, id:int, useLeftStop:bool, useRightStop:bool, maxSteps:int, minSpeed:int, maxSpeed:int) -> bool:
            '''Depricated, use motor class instead of controllerClass'''
            MCRControl.log.warning('Depricated TheiaMCR.controllerClass.MCRWriteMotorSetup, use motor.writeMotorSetup instead')
            if id == MCR_FOCUS_MOTOR_ID: retVal = MCRControl.focus.writeMotorSetup(useLeftStop, useRightStop, maxSteps, minSpeed, maxSpeed)
            elif id == MCR_ZOOM_MOTOR_ID: retVal = MCRControl.zoom.writeMotorSetup(useLeftStop, useRightStop, maxSteps, minSpeed, maxSpeed)
            elif id == MCR_IRIS_MOTOR_ID: retVal = MCRControl.iris.writeMotorSetup(useLeftStop, useRightStop, maxSteps, minSpeed, maxSpeed)
            else: retVal = False
            return retVal

        # MCRRegardLimits
        def MCRRegardLimits(self, id:int, state:bool=True, PISide:int=1) -> bool:
            '''Debricated, use motor class instead of controller class'''
            MCRControl.log.warning('Depricated TheiaMCR.controllerClass.MCRRegardLimits function, use motor.setRespectLimits instead')
            if id == MCR_FOCUS_MOTOR_ID: retVal = MCRControl.focus.setRespectLimits(state)
            elif id == MCR_ZOOM_MOTOR_ID: retVal = MCRControl.zoom.setRespectLimits(state)
            elif id == MCR_IRIS_MOTOR_ID: retVal = MCRControl.iris.setRespectLimits(state)
            else: retVal = False
            return False

        # MCRMotorInit
        def MCRMotorInit(self, id:int, steps:int, pi:int, speedRange:int, DCMotorType:bool=False) -> bool:
            '''Depricated internal function, this should not be called directly'''
            MCRControl.log.error('Depricated TheiaMCR.controllerClass.MCRMotorInit function, this should not be called directly')
            if id == MCR_FOCUS_MOTOR_ID: retVal = MCRControl.focus._motorInit(steps, pi, speedRange)
            elif id == MCR_ZOOM_MOTOR_ID: retVal = MCRControl.zoom._motorInit(steps, pi, speedRange)
            elif id == MCR_IRIS_MOTOR_ID: retVal = MCRControl.iris._motorInit(steps, pi, speedRange)
            else: retVal = False
            return retVal
        
        # MCRMove
        def MCRMove(self, id:int, steps:int, speed:int, acceleration:int=0) -> bool:
            '''Depricated internal function, this should not be called directly'''
            MCRControl.log.error('ERROR: Depricated TheiaMCR.controllerClass.MCRMove function, this should not be called directly')
            return False

        
    ######## internal use class #################################################################################################
    class MCRCom():
        initialized = err.ERR_NOT_INIT

        def __init__(self, parent, serialPortName:str=None) -> None:
            '''
            This class controlls the serial port and sends user commands to the MCR600 series board over USB serial protocol.  
            The controller board class variable 'serialPort' must be set before any functions are available. 
            The serial port name is formatted as a vitual com port ("com4" or "/dev/ttyUSB0")

            ### input:  
            - parent: the parent MCRControl class instance so all communications go through the same serial port 
            - serialPort: (optional) the serial port name ("com4") to use for communication
            ### variables:  
            - initialized (int): 0: initialized | error code (<0) if not successful
            ### global variables:  
            - serialPort is set at the MCRControl class level
            - boardCommunicationState: push the serial port state up to MCRControl class.  True if the serial port is open and communication is possible, False otherwise
            '''
            self.parent = parent
            self.serialPort = None
            self.parent.boardCommunicationState = False
            if self.parent.serialPort is None:
                try:
                    self.serialPort = serial.Serial(
                        port=serialPortName,
                        baudrate=115200,
                        bytesize=8,
                        timeout=0.1,
                        stopbits=serial.STOPBITS_ONE,
                    )
                    success = 0
                    MCRControl.log.debug(f"Serial communication opened on {serialPortName} successfully")
                except serial.SerialException as e:
                    MCRControl.log.error("Serial port not open {}".format(e))
                    err.saveError(err.ERR_SERIAL_PORT, err.MOD_MCR, err.errLine())
                    success = err.ERR_SERIAL_PORT
                self.initialized = success

        # verify communication
        def _verifyCommunication(self) -> bool:
            ''' 
            Verify communication with the MCR board by calling the readFWRevision function and reading the result.  
            If the verification fails, try to reinitialize the serial port.
            Always refer to the parent serial port and port name to make sure it is the correct instance for the port.  
            '''
            # Send a command to read the firmware revision
            cmd = bytearray([0x76, 0x0D])
            response = self._sendCmd(cmd)

            if response[1] == 0x00:
                MCRControl.log.error(f"MCR communication verified: {':'.join(f'{b:02x}' for b in response)}")
                return True
            
            # Attempt to reinitialize the serial port
            if self.parent.serialPort is not None:
                try:
                    self.parent.serialPort.close()
                except Exception as e:
                    MCRControl.log.error(f"Failed to close serial port: {e}")
                    return False

            # Attempt to reopen the serial port
            self.parent.serialPort = None
            self.restartCom = self.parent.MCRCom(self.parent, self.parent.serialPortName)
            if self.restartCom.initialized >= 0: 
                self.parent.serialPort = self.restartCom.serialPort
                self.parent.boardCommunicationRestarts += 1
            return self.restartCom.initialized == 0

        # MCRSendCmd
        def _sendCmd(self, cmd, waitTime:int=10) -> bytearray:
            '''
            Send the command through the com port over USB connection to the board.  This function should be 
            chnged for UART or I2C communication protocol instead of USB.  
            Send the byte string to the MCR-IQ board.  
            ### input: 
            - cmd: byte string to send
            - waitTime (optional): (ms) wait before checking for a response
            ### return: 
            [return byte string from MCR]
            ### globals:  
            - set self.parent.boardCommunicationState to True if the serial port is open and communication is possible, False otherwise
            '''
            response = bytearray(12)
            # check if the serial port is defined
            if isinstance(self.parent.serialPort, str):
                MCRControl.log.error("Serial port not open")
                response = bytearray([0x74, 0x01, 0x0D])
                self.parent.boardCommunicationState = False
                return response

            # send the string
            if MCRControl.communicationDebugLevel: MCRControl.log.debug("   -> {}".format(":".join("{:02x}".format(c) for c in cmd)))
            try:
                self.parent.serialPort.write(cmd)
            except (serial.SerialException, AttributeError) as e:
                MCRControl.log.error("Serial port not open ({})".format(e))
                response = bytearray([0x74, 0x01, 0x0D])
                self.parent.boardCommunicationState = False
                return response

            # wait for a response (wait first then check for the response)
            readSuccess = False
            startTime = time.time() * 1000
            while(time.time() * 1000 - waitTime < startTime): 
                # wait until finished moving (waitTime milliseconds) or until PI triggers serial port buffer response
                try:
                    if self.parent.serialPort.in_waiting > 0: 
                        break
                except serial.SerialException as e:
                    MCRControl.log.error("Serial port connection lost {}".format(e))
                    response = bytearray([0x74, 0x01, 0x0D])
                    self.parent.boardCommunicationState = False
                    return response
                time.sleep(0.1)

            # check for commands that don't generate responses, force successful response
            if cmd[0] == 0x6B:
                # set communication path
                response = bytearray([0x6B, 0x00, 0x0D])
                self.parent.boardCommunicationState = True
                return response
            ##### additional commands can be added here #####

            # read the response
            startTime = time.time() * 1000
            while (time.time() * 1000 - RESPONSE_READ_TIME < startTime): 
                # Wait until there is data waiting in the serial buffer
                try:
                    if (self.parent.serialPort.in_waiting > 0):
                        # Read data out of the buffer until a carraige return / new line is found or until 12 bytes are read
                        response = self.parent.serialPort.readline()
                        readSuccess = True
                        break
                except serial.SerialException as e:
                    MCRControl.log.error("Serial port connection lost {}".format(e))
                    response = bytearray([0x74, 0x01, 0x0D])
                    self.parent.boardCommunicationState = False
                    return response
                time.sleep(0.1)

            if not readSuccess:
                # timed out
                MCRControl.log.warning("MCR send command timed out without response")
                response = bytearray([0x74, 0x01, 0x0D])
                self.parent.boardCommunicationState = False
                return response

            # return response
            if MCRControl.communicationDebugLevel: MCRControl.log.debug("  <- None") if response == None else MCRControl.log.debug("   <- {}".format(":".join("{:02x}".format(c) for c in response)))
            self.parent.boardCommunicationState = True
            return response
        
if __name__ == "__main__":
    print("TheiaMCR")