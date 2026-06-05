# Theia Technologies motor control board interface
[Theia Technologies](https://www.theiatech.com) offers a [MCR IQ 400 motor control board](https://www.theiatech.com/lenses/accessories/mcr/) for controlling Theia's motorized lenses.  This board controls focus, zoom, iris, and IRC filter motors.  It can be connected to a host comptuer by USB, UART, or I2C connection.  

# Features
<img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="20" height="20"/> The MCR IQ 400 board (and MCR IQ 600, MCR IQ 500 and others in the MCR series) has a proprietary command protocol to control and get information from the control program.  The protocol is a customized string of up to 12 bytes which can be deciphered in the MCR IQ 400 [documentation](https://www.theiatech.com/lenses/accessories/mcr/).  For ease of use, Theia has developed this Python module to format the custom byte strings and send them to the board.  For example, the user can request the focus motor to move 1000 steps.  The `focusRel()` function will convert this request to the appropriate byte string and send it over USB connection to the MCR control board.  This will cause the lens motor to move 1000 steps.  

# Quick start
This module can be loaded into a Python program using pip.  
`pip install TheiaMCR`   
Theia's motorized lens should be connected to the MCR IQ 400 board (or similar) and the board should be connected to the host computer via USB connection thorugh a virtual com port.  The class must be initialized first using the `__init__()` function.   
``` 
# create the motor control board instance
import TheiaMCR
MCR = TheiaMCR.MCRControl(comport)
``` 
Note: `MCRControl` uses a singleton pattern — calling it a second time with the same port name returns the existing instance rather than creating a new one.  A second board can be controlled through a different port.  

After a succesful board initialization, the motors must all be initialized with their steps and limit positions.  
``` 
# initialize the motors (Theia TL1250P N6 lens parameters shown in this case)
MCR.focusInit(8390, 7959)
MCR.zoomInit(3227, 3119)
MCR.irisInit(75)
MCR.IRCInit()
```  
The initialization commands will create instances of the motor class for each motor which can be accessed by focus, zoom, and iris named instances.  If the MCRControl class was not successful (possibly due to hardware connection issue) any subsequent functions will return an error value.  There are some board query commands that use the MCRBoard subclass.  This subclass was automatically initilized.  

Motor initialization requires the number of steps and PI home position (if applicable).  These values are available in the lens spec sheet: 
- `steps`: total number of steps
- `pi`: photo interrupter (PI) home position step number (available for focus and zoom)

Focus, zoom, and iris motor init functions accept optional parameters:
- `move` (default `True`): move motor to home position on initialization
- `homingSpeed` (default: motor default speed): speed used when seeking the PI home position
- `accel` (focus/zoom only, default `0`): motor acceleration steps — reserved for future hardware support, not currently implemented

Now the motors can be controlled individually.  For example, the focus motor can be moved to an absolute step number.  
``` 
# move the focus motor
MCR.focus.moveAbs(6000)
log.info(f'Focus step {MCR.focus.currentStep}')
``` 

If the lens has an internal IRC switchable filter, the state can be 1 or 2 to match the specification sheet.  

When ending the program, call `MCR.close()` to close the serial port and release any resources being used unless they are automatically closed per OS.  

## Motor limits
The parameters for `focusInit()`, `zoomInit()`, and `irisInit()` can be found in the lens specification.  These are the parameters for some of Theia's lenses.  
- TL1250 (-N) lens: 
    - focusInit(8390, 7959)
    - zoomInit(3227, 3119)
    - irisInit(75)
- TL410 (-R) lens:
    - focusInit(9353, 8652)
    - zoomInit(4073, 154)
    - irisInit(75)
(updated v.3.5.0)

The PI position is based on the motor move direction (positive/negative) so may not be at position 0.  It is set as a known starting step number.  For example when homing the focus motor of TL1250 lens, the home position is defined as motor step 7959.  From there the lens can move to position 0 (hard stop) and, if regardLimits is off, it can move to at least position 8390.  The positive hard stop is just past the maximum step position.  Hitting either hard stop will create a mismatch in step counting and the lens must be re-homed.  

# Motor functions
Each motor (focus, zoom, iris) supports these functions:
- `motor.home()`: move motor to the PI limit switch home position
- `motor.moveAbs(step)`: move to an absolute step number
- `motor.moveRel(steps, correctForBL=True)`: move by a relative number of steps with optional backlash correction
- `motor.setMotorSpeed(speed)`: set the motor speed in pps (focus/zoom: 100–1500; iris: 10–200)
- `motor.setHomingSpeed(speed)`: set the speed in pps used when homing
- `motor.setRespectLimits(state)`: enable (`True`) or disable (`False`) enforcement of the PI limit position
- `motor.readMotorSetup()`: read motor configuration from board EEPROM
- `motor.writeMotorSetup(...)`: write motor configuration to board EEPROM

The IRC filter motor uses `MCR.IRC.state(1)` or `MCR.IRC.state(2)` to switch filter positions.

# MCRBoard functions
The `MCRBoard` subclass (initialized automatically) provides board-level queries:
- `MCR.MCRBoard.readFWRevision()`: returns the firmware version string (e.g. `'5.3.1.0.0'`)
- `MCR.MCRBoard.readBoardSN()`: returns the board serial number string
- `MCR.MCRBoard.setCommunicationPath(path)`: switch the active connection to `'USB'`, `'UART'`, or `'I2C'` — the board reboots after this command, wait >700 ms before sending further commands

To verify the serial connection is still active at any time, call `MCR.checkBoardCommunication()` which returns `True` if communication is successful.

# Important variables
Each motor has these variables available:
- `motor.currentStep`: current motor step number
- `motor.currentSpeed`: current motor speed in pulses per second (pps)
- `motor.homingSpeed`: speed in pps used when homing to the PI position
- `motor.maxSteps`: maximum number of steps for the full range of movement
- `motor.PIStep`: photointerrupter limit switch step position (within the full range of movement).  After sending the motor to home, the current step will be set to this PIStep number.
- `motor.PISide`: indicates whether the PI limit switch is on the high (`1`) or low (`-1`) step side
- `motor.respectLimits`: when `True`, moves are prevented from exceeding the PI limit position

More information about the available functions can be found in the [wiki](https://github.com/cliquot22/TheiaMCR/wiki) pages.   

# Logging
There are logging commands in the module using Python's logging libray.  These are set by default to log WARNING and higher levels.  To see other log prints in the console, initialize the class with `MCR = TheiaMCR.MCRControl("com4", moduleDebugLevel=True)` or manually set the logging level with `TheiaMCR.log.setLevel(logging.INFO)`.    
The module creates 2 rotating log files in the background by default based on Python's logging module.  If the logging module isn't used, the log files can be disabled by calling `MCR = TheiaMCR.MCRControl("com4", logFiles=False)`.  

Unhandled exceptions are logged to the log file using the `sys.excepthook` variable.  This is a global variable so check the operation within your application if you set this variable elsewhere.  

# License
[Theia Technologies BSD-3-Clause license](https://github.com/cliquot22/TheiaMCR/blob/main/LICENSE)  
Copyright 2023-2026 Theia Technologies

# Contact information
For more information contact: 
Mark Peterson at Theia Technologies
[mpeterson@theiatech.com](mailto://mpeterson@theiatech.com)

# Revision
v.3.5