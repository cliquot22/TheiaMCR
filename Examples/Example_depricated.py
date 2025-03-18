# Example for using TheiaMCR module.  
# **** These examples are for TheiaMCR earlier than v.3.0.0.  For new programs, use the latest version of TheiaMCR ****
#
# A MCR600 series control board must be connected to the Windows comptuer via USB.  Set the
# virtual comport name in the variable 'comport'
#
# Upgrade to v.3.0.0 and later: 
# - change MCR.MCRBoard.readMotorSetup() to MCR.motor.readMotorSetup() for each motor.  The return value includes one additional error status integer at the end. 
# - change MCR.MCRBoard.writeMotorSetup() to MCR.motor.writeMotorSetup() for each motor
# - no changed to MCR.focus.moveRel() and similar motor move functions.  

#import TheiaMCR as mcr     # also change __init__.py file to import the module as TheiaMCR
import TheiaMCR.TheiaMCR as mcr
import logging
import time
import serial.tools.list_ports

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

def searchComPorts():
    '''
    Search the connected com ports.  
    ### return:  
    [list of connected ports]
    '''
    ports = serial.tools.list_ports.comports()
    portList = []
    for port, desc, hwid in sorted(ports):
        log.info("Ports: {} [{}]".format(desc, hwid))
        portList.append(port)
    log.info(f'Port list: {portList}')
    return portList

def init(comport:str):
    '''
    Example: initialize the motor control board.  This will open the com port and send a test command to the board.  
    The board response should be the firmware revision.  
    ### input:  
    - comport: com port string ('com4' for example)
    '''
    # create the motor control board instance
    log.info('Initializing MCR board')
    MCR = mcr.MCRControl(comport)
    log.info('Should respond with "FW revision: #.#.#.#.#"')

def motorConfigurationDepricated(comport:str):
    '''
    Read the motor configuration for one motor (min/max speeds, max steps).  
    Set the motor configuration programatically for one motor.  
    ### input  
    - comport: com port string ('com4' for example)
    '''
    log.info('Initializing lens')
    MCR = mcr.MCRControl(comport)
    
    # initialize the motors (Theia TL1250P N6 lens in this case)
    MCR.focusInit(steps=8390, pi=7959)
    MCR.zoomInit(steps=3227, pi=3119)
    MCR.irisInit(steps=75)
    MCR.IRCInit()
    log.info('Controller board and motors sucessfully initialized')

    # check the write/read configuration for the zoom motor (id = 0x01)
    # write some data to the board (the correct values are set during motor initialization,  this will overwrite the values)
    setMaxSteps = 9000
    setMinSpeed = 200
    setMaxSpeed = 1200
    log.info(f'Write motor configuration: use stops: (True,False), max steps: {setMaxSteps}, speed range: ({setMinSpeed},{setMaxSpeed})')
    success = MCR.MCRBoard.MCRWriteMotorSetup(0x01, useLeftStop=True, useRightStop=False, maxSteps=setMaxSteps, minSpeed=setMinSpeed, maxSpeed=setMaxSpeed)
    log.info(f'(Depricated) Configuration written result: {success}')
    time.sleep(0.5)

    # read focus motor configuration (id = 0x01)
    log.info('Read motor configuration')
    success, motorType, leftStop, rightStop, maxSteps, minSpeed, maxSpeed = MCR.MCRBoard.MCRReadMotorSetup(0x01)
    if success:
        log.info(f'(Depricated) Motor type: {motorType}, use stops: ({leftStop},{rightStop}), max steps: {maxSteps}, speed range ({minSpeed},{maxSpeed})')
    else:
        log.info('(Depricated) Error reading the configuration')

def moveMotorsDepricated(comport:str, lensType:str='TL1250'):
    '''
    Example: initialize the motor control board and move motors.  
    ### input
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    '''
    # create the motor control board instance
    log.info('Initializing lens')
    MCR = mcr.MCRControl(comport)

    # initialize the motors
    if 'TL1250' in lensType:
        # TL1250 (TW60 or TW90)
        MCR.focusInit(8390, 7959)
        MCR.zoomInit(3227, 3119)
    else:
        # TL410 (TW50 or TW80)
        MCR.focusInit(9353, 8652)
        MCR.zoomInit(4073, 154)
    MCR.irisInit(75)
    MCR.IRCInit()
    time.sleep(1)

    # move the focus motor
    log.info('Move focus absolute (home and move)')
    MCR.focus.moveAbs(6000)
    log.info(f'Focus step {MCR.focus.currentStep}')
    time.sleep(1)
    log.info('Move focus relative')
    MCR.focus.moveRel(-1000)
    log.info(f'Focus step {MCR.focus.currentStep}')
    time.sleep(2)

    # move the zoom motor at a slower speed
    log.info('Move zoom at 600pps')
    MCR.zoom.setMotorSpeed(600)
    MCR.zoom.moveRel(-600)
    log.info(f'Zoom step {MCR.zoom.currentStep}')
    time.sleep(2)

    # close the iris half way
    log.info('Setting iris to 1/2 open')
    MCR.iris.moveRel(40)
    time.sleep(2)

    # switch the IRC
    log.info('Setting IRC state')
    MCR.IRCState(1)
    time.sleep(1)
    MCR.IRCState(0)
    time.sleep(2)

    # reset
    log.info('Reset lens')
    MCR.zoom.setMotorSpeed(1200)
    MCR.iris.home()

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
    #searchComPorts()
    comport = 'com4'
    #init(comport)

    #motorConfigurationDepricated(comport)
    moveMotorsDepricated(comport)
    #changeComPathExample(comport)
