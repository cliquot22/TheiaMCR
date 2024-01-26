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
The initialization commands will create instances of the motor class for each motor which can be accessed by focus, zoom, and iris named instances.  There are some board query commands that use the MCRBoard subclass.  This subclass was automatically initilized.  

Now the motors can be controlled individually.  For example, the focus motor can be moved to an absolute step number.  
``` 
# move the focus motor
MCR.focus.moveAbs(6000)
log.info(f'Focus step {MCR.focus.currentStep}')
``` 

# Important variables
Each motor has these variables available
- motor.currentStep: current motor step number
- motor.currentSpeed: current motor speed in pulses per second (pps)
- motor.maxSteps: maximum number of steps for the full range of movement
- motor.PIStep: photointerrupber limit switch step position (within the full range of movement).  After sending the motor to home, the current step will be set to this PIStep number.  

More information about the available functions can be found in the [wiki](https://github.com/cliquot22/TheiaMCR/wiki) pages.   

# License
Theia Technologies BSD license
Copyright 2023 Theia Technologies

# Contact information
For more information contact: 
Mark Peterson at Theia Technologies
[mpeterson@theiatech.com](mailto://mpeterson@theiatech.com)

# Revision
v.2.1.6