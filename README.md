# Theia Technologies motor control board interface
Theia Technologies offers a [MCR600 motor control board](https://www.theiatech.com/lenses/accessories/mcr/) for interfacing with Theia's motorized lenses.  This board controls focus, zoom, iris, and IRC filter motors.  It can be connected to a host comptuer by USB, UART, or I2C connection.  

# Features
<img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="40" height="40"/> The MCR600 board has a proprietary command protocol to control and get information from the board.  The protocol is a customized string of up to 12 bytes which can be deciphered in the MCR600 documentation.  However for ease of use, Theia has developed this Python module to format the custom byte strings and send them to the board.  The user can request the focus motor to move 1000 steps for example.  The focusRel function will convert this request to the appropriate byte string and send it over USB connection to the MCR control board.  This will cause the lens motor to move 1000 steps.  

# Quick start
This module can be loaded into a Python program.  
Theia's motorized lens should be connected to the MCR600 board and the board should be connected to the host computer via USB connection thorugh a virtual com port.  

# Functions
## Initialization functions
- MCRInit: initialize the  board
- focusInit, zoomInit, irisInit, IRCInit: initialize the appropriate motor (setup)
- focusHome, zoomHome, irisHome: move the motor to the home position
## Motor movement functions
- focusAbs, zoomAbs, irisAbs: move the motor to the home position then to an absolute step number
- focusRel, zoomRel, irisRel: move a relative number of steps
- IRCState: set the filter switch state (A/B)
## Information functions
- readFWRevision: read board firmware revision
- readBoardSN: read board serial number

# License
Theia Technologies BSD license
Copyright 2023 Theia Technologies

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Contact information
For more information contact: 
Mark Peterson at Theia Technologies
[mpeterson@theiatech.com](mailto://mpeterson@theiatech.com)

# Revision
v.1.0.8