# Example for using TheiaMCR module.  
# A MCR600 series control board must be connected to the Windows comptuer via USB.  Set the
# virtual comport name in the variable 'comport'

import TheiaMCR as mcr
import logging as log
import time

log.basicConfig(level=log.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

# virtual com port
comport = 'com4'

# create the motor control board instance
MCR = mcr.MCRControl(comport)

# initialize the motors (Theia TL1250P N6 lens in this case)
MCR.focusInit(8390, 7959)
MCR.zoomInit(3227, 3119)
MCR.irisInit(75)
MCR.IRCInit()
time.sleep(1)

# move the focus motor
MCR.focus.moveAbs(6000)
log.info(f'Focus step {MCR.focus.currentStep}')
MCR.focus.moveRel(-1000)
log.info(f'Focus step {MCR.focus.currentStep}')
time.sleep(1)

# move the zoom motor at a slower speed
MCR.zoom.setMotorSpeed(600)
MCR.zoom.moveRel(-600)
log.info(f'Zoom step {MCR.zoom.currentStep}')
time.sleep(1)

# close the iris half way
MCR.iris.moveRel(40)

# switch the IRC
MCR.IRCState(1)
time.sleep(1)
MCR.IRCState(0)