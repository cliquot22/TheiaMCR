# Example for using TheiaMCR module.  
# A MCR600 series control board must be connected to the Windows comptuer via USB.  Set the
# virtual comport name in the variable 'comport'

import TheiaMCR as mcr
#import TheiaMCR.TheiaMCR as mcr  # use for local development
import logging
import time
import os
import serial.tools.list_ports

def searchComPorts():
    '''
    Search the connected com ports.  
    ### return:  
    [list of connected ports]
    '''
    ports = serial.tools.list_ports.comports()
    portList = []
    for port, desc, hwid in sorted(ports):
        if ((os.name == 'posix') and (hwid != 'n/a')):
            log.info("Ports: {} [{}]".format(desc, hwid))
            portList.append(port)
        elif os.name == 'nt':
            log.info("Ports: {} [{}]".format(desc, hwid))
            portList.append(port)
    log.info(f'Port list: {portList}')
    return portList

def init(comport:str, lensType:str='TL1250', moduleDebugLevel=False, communicationDebugLevel=False, logFiles=True):
    '''
    Example: initialize the motor control board.  This will open the com port and send a test command to the board.  
    The board response should be the firmware revision.  
    Next initialize the motors of the lens through the new controller board.  
    ### input:  
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    - moduleDebugLevel: (optional:False) to see debug level logging from the MCR module
    - communicationDebugLevel: (optional:False) to see debug level logging from the MCR module
    - logFiles: (optional:True) to create a log file in the AppData/Local/TheiaMCR/log directory
    ### return:  
    - handle to the MCR class
    '''
    # create the motor control board instance
    log.info('Initializing MCR board')
    MCR = mcr.MCRControl(serialPortName=comport, moduleDebugLevel=moduleDebugLevel, communicationDebugLevel=communicationDebugLevel, logFiles=logFiles)
    log.info('Response (above) in the form: "FW revision: #.#.#.#.#"')
    
    # initialize the motors
    if 'TL1250' in lensType:
        # TL1250 (TW60 or TW90)
        MCR.focusInit(steps=8390, pi=7959)
        MCR.zoomInit(steps=3227, pi=3119)
    else:
        # TL410 (TW50 or TW80)
        MCR.focusInit(steps=9353, pi=8652)
        MCR.zoomInit(steps=4073, pi=154)
    MCR.irisInit(75)
    MCR.IRCInit()
    log.info(f'MCR initialized ({MCR.MCRInitialized}) for logging')
    log.info(f'MCR board initialized: {MCR.boardInitialized}')
    time.sleep(1)
    return MCR

def motorConfiguration(comport:str, lensType:str='TL1250'):
    '''
    Read the motor configuration for one motor (min/max speeds, max steps).  
    Set the motor configuration programatically for one motor.  
    ### input  
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)

    # check the write/read configuration for the zoom motor
    # write some data to the board (the correct values are set during motor initialization,  this will overwrite the values)
    setMaxSteps = 9000
    setMinSpeed = 200
    setMaxSpeed = 1200
    log.info(f'Write motor configuration: use stops: (True,False), max steps: {setMaxSteps}, speed range: ({setMinSpeed},{setMaxSpeed})')
    success = MCR.zoom.writeMotorSetup(useWideFarStop=True, useTeleNearStop=False, maxSteps=setMaxSteps, minSpeed=setMinSpeed, maxSpeed=setMaxSpeed)
    log.info(f'Configuration written result: {success}')
    time.sleep(0.5)

    # read focus motor configuration (id = 0x01)
    log.info('Read motor configuration')
    success, motorType, leftStop, rightStop, maxSteps, minSpeed, maxSpeed, errorVal = MCR.zoom.readMotorSetup()
    if success:
        log.info(f'Motor type: {motorType}, use stops: ({leftStop},{rightStop}), max steps: {maxSteps}, speed range ({minSpeed},{maxSpeed}), error: {errorVal}')
    else:
        log.info('Error reading the configuration')

def moveMotorsExample(comport:str, lensType:str='TL1250'):
    '''
    Example: initialize the motor control board and move motors.  
    ### input
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)

    # move the focus motor
    log.info('Move focus absolute (home and move) to step 6000')
    MCR.focus.moveAbs(6000)
    log.info(f'Final Focus step {MCR.focus.currentStep}')
    time.sleep(1)
    log.info('Move focus relative by -1000')
    MCR.focus.moveRel(-1000)
    log.info(f'Final Focus step {MCR.focus.currentStep}')
    time.sleep(2)

    # move the zoom motor at a slower speed
    log.info(f'Initial zoom step (PI) {MCR.zoom.currentStep}')
    direction = -1 if 'TL1250' in lensType else 1
    log.info(f'Move zoom at 600pps by {"-" if direction < 0 else ""}600 steps')
    MCR.zoom.setMotorSpeed(600)
    MCR.zoom.moveRel(direction * 600)
    log.info(f'Final Zoom step {MCR.zoom.currentStep}')
    time.sleep(2)

    # close the iris half way
    log.info('Setting iris to 1/2 open')
    MCR.iris.moveRel(40)
    log.info(f'Final iris step {MCR.iris.currentStep}')
    time.sleep(2)

    # switch the IRC
    log.info('Setting IRC state')
    MCR.IRC.state(1)
    time.sleep(1)

    # reset
    log.info('Reset lens')
    MCR.zoom.setMotorSpeed(1200)
    log.info('Open iris')
    MCR.iris.home()
    log.info('Reset IRC state')
    MCR.IRC.state(0)
    log.info('Focus and zoom remain at their set positions')

def limits(comport:str, lensType:str='TL1250'):
    '''
    Turn off the limit check to allow the lens to attempt to move past the PI position.  This may be required to achieve 
    focus (especially at some focal lengths of the TL410 lens).  
    ### input:  
    - comport: the com port string
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)

    # home focus motor
    log.info(f'Homing focus motor to PI position {MCR.focus.PIStep}')
    MCR.focus.home()
    log.info(f'Focus motor at {MCR.focus.currentStep} (home)')
    time.sleep(1)

    # move beyond PI position
    log.info('Moving past PI position by 200 steps (correct for backlash should be off for this move)')
    MCR.focus.setRespectLimits(False)
    MCR.focus.moveRel(steps=200, correctForBL=False)
    log.info(f'Focus motor at {MCR.focus.currentStep}')
    time.sleep(2)

    # move to home
    log.info('Moving motor back to home position')
    MCR.focus.home()
    log.info(f'Focus motor at {MCR.focus.currentStep} (home)')

    # turn PI limit back on.  
    MCR.focus.setRespectLimits(True)

def closeLogFile(comport:str, lensType:str='TL1250'):
    '''
    Start with the normal logging to file (in AppData/Local/TheiaMCR/log) and then close the file to stop logging.  
    Stream console logging should continue.   
    ### input:  
    - comport: the com port string
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)

    # stop logging moves
    MCR.closeLogFiles()
    MCR.focus.home()

def close(comport:str):
    '''
    Open and initialize the board.  Then close everything to clean up resources simulating the end of a program.  
    ### input
    - comport: com port string ('com4' for example)
    '''
    MCR = init(comport)
    log.info('Closing down')
    MCR.close()
    log.info('Resources released, this should give an ERROR:')
    try: 
        MCR.MCRBoard.readBoardSN()
    except:
        log.info('ERROR: No board response')

def viewCommunications(comport:str):
    '''
    This function demonstrates the low level byte string communication with the board.  If you want to format and send/read byte strings 
    yourself, this demonstration function will help show the strings.  Normally, this level of detail is not required.  

    View byte strings sent to and received from the board.  After a move command, the response buffer will be updated.  To make sure the response 
    is from the most recent move, request the board FW revision or SN between each move and read the response.  
    ### input:  
    - comport: the com port string
    '''
    MCR = init(comport)

    # set up to see logging from TheiaMCR
    mcr.MCRControl.communicationDebugLevel = True     # be sure to set the class variable, not the instance variable

    # move the lens
    log.info('Move the lens using 0x62 or 0x66 depending on direction')
    response = MCR.focus.moveRel(-500)
    log.info(f'moveRel function response will be 0 or error value, response = {response}')
    
    # clear the response buffer
    log.info('Clear the response buffer')
    response = MCR.MCRBoard.readBoardSN()
    log.info(f'readBoardSN function response is SN: {response}')
    
    # move the lens
    log.info('Move the lens again')
    response = MCR.focus.moveRel(500)
    log.info(f'moveRel function response will be 0 or error value, response = {response}')

    # reset
    mcr.MCRControl.communicationDebugLevel = False


def changeComPathExample(comport:str):
    '''
    Example: change the communication path to the board.  
    New com path can be a string name or integer ['USB' | 1, 'UART' | 2, 'I2C' | 0].    
    Set the new path in the function but beware that communication over USB will be disabled and the board
    will have to be factory reset to restore USB communication.  
    See section 3.3.6 in the operator's manual for factory reset of the board at https://theiatech.com/mcr
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
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

    # lens types
    lensTypes = ['TL410', 'TL1250']
    # test selection
    # 1: search com ports and list all connected devices
    # 2: initialize the board and motors
    # 3: read and write a motor configuration (steps, speed, etc.)
    # 4: move motors
    # 5: turn off PI limit to show moving past PI position
    # 6: close the background logging file 
    # 7: close and release resources before exiting a program
    # 8: (low level) show the byte string communications back and forth to the board 
    # 9: change the input protocol from USB to UART or I2C 
    
    runTest = [2,4]   ### select the test numbers to run (can be multiple)
    lensType = 1    # 0: 'TL410', 1: 'TL1250'
    
    if os.name == 'nt':
        comport = 'com4'
    else:
        comport = '/dev/ttyUSB0'
        # in Lunux make sure there is permission to access the port (sudo usermod -a -G dialout $USER)
    if 0 in runTest or len(runTest) == 0:
        log.info('Set the test numbers in the variable "runTest"')
    if 1 in runTest:
        log.info('1: search com ports and list all connected devices')
        searchComPorts()
    if 2 in runTest:
        log.info('2: initialize the board and motors')
        init(comport, lensTypes[lensType], moduleDebugLevel=False)
    if 3 in runTest:
        log.info('3: read and write a motor configuration (steps, speed, etc.)')
        motorConfiguration(comport)
    if 4 in runTest:
        log.info('4: move motors')
        moveMotorsExample(comport, lensTypes[lensType])
    if 5 in runTest:
        log.info('5: turn off PI limit to show moving past PI position')
        limits(comport, lensTypes[lensType])
    if 6 in runTest:
        log.info('6: close the background logging file')
        closeLogFile(comport, lensTypes[lensType])
    if 7 in runTest:
        log.info('7: close and release resources before exiting a program')
        close(comport)

    ##### special demonstration functions ######
    if 8 in runTest:
        log.info('8: (low level) show the byte string communications back and forth to the board')
        viewCommunications(comport)
    if 9 in runTest:
        log.info('9: change the input protocol from USB to UART or I2C')
        changeComPathExample(comport)
    log.info('Done')