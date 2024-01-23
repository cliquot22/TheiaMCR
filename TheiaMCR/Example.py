# Example for using TheiaMCR module.  
# A MCR600 series control board must be connected to the Windows comptuer via USB.  Set the
# virtual comport name in the variable 'comport'

import TheiaMCR as mcr
import logging as log
import time

log.basicConfig(level=log.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

def moveMotorsExample(comport:str):
    '''
    Example: initialize the motor control board and move motors.  
    ### input
    - comport: com port string ('com4' for example)
    '''
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

def changeComPathExample(comport:str):
    '''
    Example: change the communication path to the board.  
    New com path can be a string name or integer ['USB' | 1, 'UART' | 2, 'I2C' | 0].    
    Set the new path in the function but beware that communication over USB will be disabled and the board
    will have to be factory reset to restore USB communication.  
    See the driver instructions in the "specifications and instructions" folder at https://theiatech.com/mcr
    ### input
    - comport: com port string ('com4' for example)
    '''
    # create the motor control board instance
    MCR = mcr.MCRControl(comport)
    time.sleep(1)

    # new communication path
    log.info('Setting new communications path')
    MCR.MCRBoard.setCommunicationPath('USB')

    # wait >700ms for board to reboot
    time.sleep(1)

if __name__ == '__main__':
    # virtual com port
    comport = 'com4'

    moveMotorsExample(comport)
    #changeComPathExample(comport)