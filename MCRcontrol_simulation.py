# MCR control module (simulation for use without connected MCR600)
# this module does the USB control of the MCR600 board to control lens motors
# 
# call MCRInit(comPort name) and check for success.  This will check the com port is open and
#   also if a response is received from the test command (FW version request)
# initialize motors with focusInit, zoomInit, irisInit, IRCInit to set max steps and speed ranges
# home motors with focusHome, zoomHome, irisHome, and IRCHome to set motors to PI or 0 limits
#
# v.1.0.0 220217
import serial
import TheiaMCR.errList as err
import logging as log

# debugging
tracePrintMCR = False                   # set for full printout

# communication
serialPort = ''

# internal variables
# constants
OK = 0
constMCRFocusMotor = 0x01
constMCRZoomMotor = 0x02
constMCRIrisMotor = 0x03
constMCRIRCMotor = 0x04
constMCRIRCSwitchTime = 50              # (ms) switch time for IRC
constMCRFZDefaultSpeed = 1000           # (pps) default focus/zoom motor speeds
constMCRIrisDefaultSpeed = 100          # (pps) default iris motor speed
constBacklash = 60                      # used to remove lens backlash, this should exceed lens maximum backlash amount

# current step positions
MCRFocusStep = 0
MCRZoomStep = 0
MCRIrisStep = 0

# other setup variables
MCRFocusStepsMax = 0
MCRZoomStepsMax = 0
MCRIrisStepsMax = 0
MCRFocusPI = 0
MCRFocusPISide = 1                      # set to 1 for high side, -1 for low side
MCRFocusRespectLimit = True             # set True to respect PI limits
MCRFocusAcceleration = 0                # motor step acceleration
MCRZoomPI = 0
MCRZoomPISide = 1                       # set to 1 for high side, -1 for low side
MCRZoomRespectLimit = True
MCRZoomAcceleration = 0


#-------------------------------------------------------------------------------
# MCRInit
# initialize the MCR board before any commands can be sent
# this does not initialize motor steps and positions
# input: com: the com port name of the board (e.g. "com21")
#       tracePrint (optional): set to print all commands in the console
# globals: create a serialPort for writing
#           tracePrintMCR for debugging
# return: success integer value (comport > 0 == True)
#           err_serial_port: serial port not available
def MCRInit(com:str, tracePrint:bool=False):
    success = 4
    global serialPort, tracePrintMCR, MCRZoomRespectLimit, MCRFocusRespectLimit
    tracePrintMCR = tracePrint
    
    # set initial PI respect limit state
    MCRZoomRespectLimit = True
    MCRFocusRespectLimit = True
    return success

# focusInit
# initialize the parameters of the focus motor
# input: steps: maximum number of steps
#       pi: pi location in step number
#       move: (optional, True) move motor to home position
#       accel: (optional, 0) motor acceleration steps
# globals: set MCRFocusPI and MCRFocusStepsMax and MCRFocusPISide, MCRFocusAcceleration
# return: focus motor step position
#       propogate errors: err_not_init: PI was not set
#                       no PI was triggered
def focusInit(steps:int, pi:int, move:bool = True, accel:int=0) -> tuple[int, int]:
    global MCRFocusPI, MCRFocusStepsMax, MCRFocusPISide, MCRFocusAcceleration
    MCRFocusPI = pi
    MCRFocusStepsMax = steps
    # set acceleration
    MCRFocusAcceleration = accel << 3 | 0x01

    # set PI side
    if (steps - pi) < pi:
        MCRFocusPISide = 1
    else:
        MCRFocusPISide = -1
    success = True
    if not success:
        err.saveError(err.ERR_NOT_INIT, err.MOD_MCR, err.errLine())
        return err.ERR_NOT_INIT, 0
    pos = 0
    error = OK
    if move:
        error, pos = focusHome()
        if error != 0:
            err.saveError(error, err.MOD_MCR, err.errLine())
    return error, pos

# focusHome
# send the focus to the PI location
# globals: set MCRFocusStep
# return: the PI step position of the motor
#       err_bad_move: PI was nto set (call focusInit first)
#       err_bad_move: no PI was triggered
def focusHome() -> tuple[int, int]:
    global MCRFocusStep
    if MCRFocusPI == 0:
        log.warning("Error: no focus PI set")
        err.saveError(err.ERR_PI_NOT_INIT, err.MOD_MCR, err.errLine())
        return err.ERR_PI_NOT_INIT, 0
    
    # determine direction of PI
    steps = MCRFocusStepsMax * MCRFocusPISide
    
    # move the motor
    success = True
    if success:
        MCRFocusStep = MCRFocusPI
    else:
        log.error("Error: Focus motor move error")
        MCRFocusStep = 0
        err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
        return err.ERR_BAD_MOVE, 0

    return OK, MCRFocusStep

# zoomInit
# initialize the parameters of the zoom motor and home the motor
# input: steps: maximum number of steps
#       pi: pi location in step number
#       move: (optional, True) move motor to home position
#       accel: (optional, 0) motor acceleration steps
# globals: set MCRZoomPI, MCRZoomStepsMax, MCRZoomPISide, MCRZoomAcceleration
# return: zoom step position
#       propogate errors: err_not_init: PI was not set
#                       err_bad_move: home PI was not triggered
def zoomInit(steps:int, pi:int, move:bool = True, accel:int=0) -> tuple[int, int]:
    global MCRZoomPI, MCRZoomStepsMax, MCRZoomPISide, MCRZoomAcceleration
    MCRZoomPI = pi
    MCRZoomStepsMax = steps
    # set acceleration
    MCRZoomAcceleration = accel << 3 | 0x01

    # set PI side
    if (steps - pi) < pi:
        MCRZoomPISide = 1
    else:
        MCRZoomPISide = -1
    success = True
    pos = 0
    error = OK
    if move:
        error, pos = zoomHome()
        if error != 0:
            err.saveError(error, err.MOD_MCR, err.errLine())
    return error, pos

# zoomHome
# send the zoom to the PI location
# globals: set MCRZoomStep
# return: the PI step position of the motor
#       err_not_init: PI was not set (call zoomInit first)
#       err_bad_move: home PI was not triggered
def zoomHome() -> tuple[int, int]:
    global MCRZoomStep
    if MCRZoomPI == 0:
        log.warning("Error: no zoom PI set")
        err.saveError(err.ERR_PI_NOT_INIT, err.MOD_MCR, err.errLine())
        return err.ERR_PI_NOT_INIT, 0
    
    # determine direction of PI
    steps = MCRZoomStepsMax * MCRZoomPISide
    
    # move the motor
    success = True
    if success:
        MCRZoomStep = MCRZoomPI
    else:
        log.error("Error: Zoom motor move error")
        MCRZoomStep = 0
        err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
        return err.ERR_BAD_MOVE, 0

    return OK, MCRZoomStep

#---------- focus/zoom motor move ------------------------------------------------------------
# focusAbs
# move the focus motor to absolute step number
# input: step: the step to move to
#       speed (optional): the pps speed
# globals: set MCRFocusStep
# return: the final step number
#       err_bad_move: if there is a home error
#       err_param: if there is an input error
def focusAbs(step, speed = 1000):
    global MCRFocusStep
    if step < 0:
        log.error("Error: focus cannot move abs < 0")
        return err.ERR_RANGE, 0

    # move to PI position
    error, res = focusHome()
    if error != 0:
        log.error("Error: focus home error")
        err.saveError(error, err.MOD_MCR, err.errLine())
        return error, 0

    # move to absolute position
    steps = step - MCRFocusPI
    error, finalStep = focusRel(steps, speed)
    if error != 0:
        # propogate error
        err.saveError(error, err.MOD_MCR, err.errLine())
        return error, 0
    return OK, finalStep

# focusRel
# move the focus motor by a number of steps
# this doesn't account for any backlash in the motor
# steps won't exceed the motor limits but PI trigger will stop the motor so step count may be off
# input: steps: the number of steps to move
#       speed (optional): the pps speed
#       correctForBL (optional): set true to move from PI side
# global: set MCRFocusStep
# return: error,
#       the final step number
def focusRel(steps, speed = 1000, correctForBL = True):
    global MCRFocusStep
    if steps == 0:
        return OK, MCRFocusStep

    # check for limits
    limit, steps = focusCheckLimits(steps, MCRFocusRespectLimit)
    if MCRFocusRespectLimit and (limit != 0):
        log.warn(f'Limiting focus relative steps to {steps}')

    # move the motor
    success = True
        
    if success:
        MCRFocusStep += steps
    else:
        MCRFocusStep = 0
        err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
        return err.ERR_BAD_MOVE, 0

    return OK, MCRFocusStep

# focusCheckLimits
# check if the target step will exceed limits
# if limitStep is True, the lens won't pass the PI limit
# 210809 fixed bug to prevent moving past side opposit PI limit
# input: steps: target steps
#       limitStep: (optional) set True to limit steps, False to only warn
# return: retVal
#           2: steps exceed maximum steps
#           1: steps exceed high PI
#           0: steps will not cause exceeding limits
#           -1: steps exceed low PI
#           -2: steps exceed minimum steps
#       retSteps: new target steps depending on limitStep setting
def focusCheckLimits(steps, limitStep = False):
    retSteps = steps
    retVal = 0
    if limitStep and (MCRFocusPISide > 0) and (MCRFocusStep + steps > MCRFocusPI):
        if limitStep:
            retSteps = max(MCRFocusPI - MCRFocusStep, 0)
        log.warning("Warn: focus steps exceeds PI")
        retVal = 1
    elif limitStep and (MCRFocusPISide < 0) and (MCRFocusStep + steps < MCRFocusPI):
        if limitStep:
            retSteps = min(MCRFocusPI - MCRFocusStep, 0)
        log.warning("Warn: focus steps exceeds low PI")
        retVal = -1
    elif MCRFocusStep + steps > MCRFocusStepsMax:
        if limitStep:
            retSteps = max(MCRFocusStepsMax - MCRFocusStep, 0)
        log.warning("Warn: focus steps exceeds maximum")
        retVal = 2
    elif MCRFocusStep + steps < 0:
        if limitStep:
            retSteps = min(-MCRFocusStep, 0)
        log.warning("Warn: focus steps exceeds minimum")
        retVal = -2
    return retVal, retSteps

# zoomAbs
# move the zoom motor to absolute step number
# input: step: the step to move to
#       speed (optional): the pps speed
# return: the final step number
#       err_bad_move: if there is a home error
#       err_param: if there is an input error
def zoomAbs(step, speed = 1000):
    if step < 0:
        log.error("Error: zoom cannot move abs < 0")
        return err.ERR_RANGE, 0

    # move to PI position
    error, res = zoomHome()
    if res <= 0:
        log.error("Error: zoom home error")
        err.saveError(error, err.MOD_MCR, err.errLine())
        return error, 0

    # move to absolute position
    steps = step - MCRZoomPI
    error, finalStep = zoomRel(steps, speed)
    if error != 0:
        # propogate error
        err.saveError(error, err.MOD_MCR, err.errLine())
        return error, 0
    return OK, finalStep

# zoomRel
# move the zoom motor by a number of steps
# this doesn't account for any backlash in the motor
# steps won't exceed the movement limits.  PI trigger will stop the motor so step count may be off
# input: steps: the number of steps to move
#       speed (optional): the pps speed
#       correctForBL (optional): set true to be sure movement comes from PI side
# globals: set MCRZoomStep
# return: the final step number
#       err_bad_move: if there is an error
def zoomRel(steps, speed = 1000, correctForBL = True):
    global MCRZoomStep
    if steps == 0:
        return OK, MCRZoomStep 
        
    # check for limits
    limit, steps = zoomCheckLimits(steps, MCRZoomRespectLimit)
    if MCRZoomRespectLimit and (limit != 0):
        log.warn(f'Limiting zoom relative steps to {steps}')

    # move the motor
    success = True

    if success:
        MCRZoomStep = MCRZoomStep + steps
    else:
        MCRZoomStep = 0
        err.saveError(err.ERR_BAD_MOVE, err.MOD_MCR, err.errLine())
        return err.ERR_BAD_MOVE, 0

    return OK, MCRZoomStep

# zoomCheckLimits
# check if the target step will exceed limits
# 210809 fixed bug updated to prevent exceeding side opposit PI limit
# input: steps: target steps
#       limitStep: (optional) set True to limit steps, False to only warn
# return: retVal
#           2: steps exceed maximum steps
#           1: steps exceed high PI
#           0: steps will not cause exceeding limits
#           -1: steps exceed low PI
#           -2: steps exceed minimum steps
#       retSteps: new target steps depending on limitStep setting
def zoomCheckLimits(steps, limitStep = False):
    retSteps = steps
    retVal = 0
    if limitStep and (MCRZoomPISide > 0) and (MCRZoomStep + steps > MCRZoomPI):
        if limitStep:
            retSteps = max(MCRZoomPI - MCRZoomStep, 0)
        log.warning("Warn: zoom steps exceeds PI")
        retVal = 1
    elif limitStep and (MCRZoomPISide < 0) and (MCRZoomStep + steps < MCRZoomPI):
        if limitStep:
            retSteps = min(MCRZoomPI - MCRZoomStep, 0)
        log.warning("Warn: zoom steps exceeds low PI")
        retVal = -1
    elif MCRZoomStep + steps > MCRZoomStepsMax:
        if limitStep:
            retSteps = max(MCRZoomStepsMax - MCRZoomStep, 0)
        log.warning("Warn: zoom steps exceeds maximum")
        retVal = 2
    elif MCRZoomStep + steps < 0:
        if limitStep:
            retSteps = min(-MCRZoomStep, 0)
        log.warning("Warn: zoom steps exceeds minimum")
        retVal = -2
    return retVal, retSteps

#----------- iris/IRC ---------------------------------------------------------------------------------
# irisInit
# initialize the parameters of the iris motor
# NOTE: Iris step direction for MCR is reversed (0x66(+) is closed) so invert step direction before moving
# input: steps: maximum number of steps
#       move (optional): move to home position
# globals: set MCRIrisStepsMax
# return: iris step position (home)
def irisInit(steps, move = True):
    global MCRIrisStepsMax
    #success = MCRMotorInit(constMCRIrisMotor, steps, 0)
    MCRIrisStepsMax = steps
    pos = 0
    if move:
        pos = irisHome()
    return OK, pos

# irisHome
# send the iris to the 0 (full open) position
# global: set MCRIrisStep
# return: iris step number
def irisHome():
    global MCRIrisStep

    # move the motor
    #MCRMove(constMCRIrisMotor, -MCRIrisStepsMax, constMCRIrisDefaultSpeed)
    MCRIrisStep = 0
    return MCRIrisStep

# irisRel
# move the iris by relative number of steps
# Iris can move against hard stops but returned step will be limited to the range
# input: steps to move
# global: set MCRIrisStep
# return: final step
def irisRel(steps):
    global MCRIrisStep
    #MCRMove(constMCRIrisMotor, steps, constMCRIrisDefaultSpeed)

    # set position tracking
    MCRIrisStep += steps
    MCRIrisStep = min(MCRIrisStep, MCRIrisStepsMax)
    MCRIrisStep = max(MCRIrisStep, 0)
    return MCRIrisStep

# irisAbs
# more iris to absolute position
# input: steps
# return: final step
def irisAbs(steps):
    irisHome()
    finalStep = irisRel(steps)
    return finalStep

# MCRRegardLimits
# set the limit switches to true/false
# input: id: motor id (focus/zoom)
#       state: set limits
# globals: set MCRFocusRespectLimit
#           set MCRZoomRespectLimit
# return: true if MCR returned a valid response
def MCRRegardLimits(id:int, state:bool=True) -> bool:
    global MCRFocusRespectLimit, MCRZoomRespectLimit
    
    # set the global variables
    if id == constMCRFocusMotor:
        MCRFocusRespectLimit = state
    else:
        MCRZoomRespectLimit = state
    return True