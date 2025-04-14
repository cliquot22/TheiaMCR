# Theia Technologies motor control board interface
[Theia Technologies](https://www.theiatech.com) offers a [MCR600 motor control board](https://www.theiatech.com/lenses/accessories/mcr/) for controlling Theia's motorized lenses.  This board controls focus, zoom, iris, and IRC filter motors.  It can be connected to a host comptuer by USB, UART, or I2C connection.  

# Features
<img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="20" height="20"/> The MCR600 board (and MCR400, MCR500 and others in the MCR series) has a proprietary command protocol to control and get information from the board.  The protocol is a customized string of up to 12 bytes which can be deciphered in the MCR600 [documentation](https://www.theiatech.com/lenses/accessories/mcr/).  For ease of use, Theia has developed this Python module to format the custom byte strings and send them to the board.  For example, the user can request the focus motor to move 1000 steps.  The `focusRel()` function will convert this request to the appropriate byte string and send it over USB connection to the MCR control board.  This will cause the lens motor to move 1000 steps.  

# Quick start
This module can be loaded into a Python program using pip.  
`pip install TheiaMCR`   
Theia's motorized lens should be connected to the MCR600 board and the board should be connected to the host computer via USB connection thorugh a virtual com port.  The class must be initizlized first using the `__init__()` function.   
``` 
# create the motor control board instance
MCR = mcr.MCRControl(comport)
``` 

Then the motors must all be initialized with their steps and limit positions.  
``` 
# initialize the motors (Theia TL1250P N6 lens in this case)
MCR.focusInit(8390, 7959)
MCR.zoomInit(3227, 3119)
MCR.irisInit(75)
MCR.IRCInit()
```  
The initialization commands will create instances of the motor class for each motor which can be accessed by focus, zoom, and iris named instances.  If the MCRControl class was not successful (possibly due to hardware connection issue) any subsequent functions will return an error value.  There are some board query commands that use the MCRBoard subclass.  This subclass was automatically initilized.  

Now the motors can be controlled individually.  For example, the focus motor can be moved to an absolute step number.  
``` 
# move the focus motor
MCR.focus.moveAbs(6000)
log.info(f'Focus step {MCR.focus.currentStep}')
``` 

For the internal IRC switchable filter, the state can be 1 or 2 to match the specification sheet.  Usually filter 1 is visible only transmission and filter 2 is visible + IR transmission.  

When ending the program, call `MCR.close()` to close the serial port and release any resources being used.  

## Motor limits
The parameters for `focusInit()`, `zoomInit()`, and `irisInit` can be found in the lens specification.  These are the parameters for some of Theia's lenses.  
- TL1250 (-N) lens: 
    - focusInit(8390, 7959)
    - zoomInit(3227, 3119)
    - irisInit(75)
- TL410 (-R) lens:
    - focusInit(9353, 8652)
    - zoomInit(4073, 154)
    - irisInit(75)
(updated v.2.5.0)

# Important variables
Each motor has these variables available
- motor.currentStep: current motor step number
- motor.currentSpeed: current motor speed in pulses per second (pps)
- motor.maxSteps: maximum number of steps for the full range of movement
- motor.PIStep: photointerrupber limit switch step position (within the full range of movement).  After sending the motor to home, the current step will be set to this PIStep number.  

More information about the available functions can be found in the [wiki](https://github.com/cliquot22/TheiaMCR/wiki) pages.   

# Logging
There are logging commands in the module using Python's logging libray.  These are set by default to log WARNING and higher levels.  To see other log prints in the console, initialize the class with `MCR = TheiaMCR.MCRControl(serial_port="com4", degubLog=True)` or manually set the logging level with `TheiaMCR.log.setLevel(logging.INFO)`.    
The module creates 2 rotating log files in the background by default based on Python's logging module.  If the logging module isn't used, the log files can be disabled by calling `MCR = TheiaMCR.MCRControl(serial_port="com4", logFiles=False)`.  

Unhandled exceptions are logged to the log file using the `sys.excepthook` variable.  This is a global variable so check the operation within your application if you set this variable elsewhere.  

# License
Theia Technologies BSD license
Copyright 2023-2025 Theia Technologies

# Contact information
For more information contact: 
Mark Peterson at Theia Technologies
[mpeterson@theiatech.com](mailto://mpeterson@theiatech.com)

# Revision
v.3.1