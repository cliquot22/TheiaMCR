# Example for using TheiaMCR module.
# A MCR600 series control board must be connected to the computer via USB.
# Run this file and follow the console prompts to select the com port, lens type, and the examples to run.
#
# updated for MCR version 3.5
#
# pyright: reportOptionalMemberAccess=false

import TheiaMCR as mcr
import logging
import time
import os
import serial.tools.list_ports
import sys
import gc
import re

lensTypes = ['TL410', 'TL1250']

# example tests (number: description)
tests = {
    1: 'initialize the board and motors',
    2: 'read and write a motor configuration (steps, speed, etc.)',
    3: 'move motors',
    4: 'turn off PI limit to show moving past PI position',
    5: 'close the background logging file',
    6: 'close and release resources before exiting a program',
    7: '(low level) show the byte string communications back and forth to the board',
    8: 'change the input protocol from USB to UART or I2C',
    9: 'reconnect to the com port in case of lost connection',
}


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
    - handle to the MCR class or None if the board did not initialize
    '''
    # create the motor control board instance
    log.info('Initializing MCR board')
    MCR = mcr.MCRControl(serialPortName=comport, moduleDebugLevel=moduleDebugLevel, communicationDebugLevel=communicationDebugLevel, logFiles=logFiles)
    if not MCR.boardInitialized:
        log.error(f'Board did not initialize on {comport}.  Select the correct com port (option "c" in the menu)')
        release(MCR)
        return None
    log.info('Response (above) in the form: "FW revision: #.#.#.#.#"')

    # initialize the motors
    # NOTE: not including homingSpeed in focusInit(), etc. will set the speed to default.  Ignore the warning from MCR.
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
    if MCR is None: return None

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
    if not MCR.zoom.initialized:
        log.error('Zoom lens initialization failed in init() function')
        return MCR
    # or check for zoom motor not initizlized afterwards with try: \ success... = MCR.zoom.readMotorSetup() \ if success... \ except (ValueError, TypeError): ...
    success, motorType, leftStop, rightStop, maxSteps, minSpeed, maxSpeed, errorVal = MCR.zoom.readMotorSetup()  #type: ignore
    if success:
        log.info(f'Motor type: {motorType}, use stops: ({leftStop},{rightStop}), max steps: {maxSteps}, speed range ({minSpeed},{maxSpeed}), error: {errorVal}')
    else:
        log.info('Error reading the configuration')
    return MCR

def moveMotorsExample(comport:str, lensType:str='TL1250'):
    '''
    Example: initialize the motor control board and move motors.
    ### input
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)
    if MCR is None: return None

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
    return MCR

def limits(comport:str, lensType:str='TL1250'):
    '''
    Turn off the limit check to allow the lens to attempt to move past the PI position.  This may be required to achieve
    focus (especially at some focal lengths of the TL410 lens).
    ### input:
    - comport: the com port string
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)
    if MCR is None: return None

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
    return MCR

def closeLogFile(comport:str, lensType:str='TL1250'):
    '''
    Start with the normal logging to file (in AppData/Local/TheiaMCR/log) and then close the file to stop logging.
    Stream console logging should continue.
    ### input:
    - comport: the com port string
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)
    if MCR is None: return None

    # stop logging moves
    MCR.closeLogFiles()
    MCR.focus.home()
    return MCR

def close(comport:str):
    '''
    Open and initialize the board.  Then close everything to clean up resources simulating the end of a program.
    ### input
    - comport: com port string ('com4' for example)
    '''
    MCR = init(comport)
    if MCR is None: return None
    log.info('Closing down')
    MCR.close()
    log.info('Resources released, this should give an ERROR:')
    try:
        MCR.MCRBoard.readBoardSN()
    except:
        log.info('ERROR: No board response')

    # Explicitly delete the MCR variable to ensure Windows releases the COM port handle
    del MCR
    gc.collect()
    return None

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
    if MCR is None: return None

    # set up to see logging from TheiaMCR
    mcr.MCRControl.communicationDebugLevel = True     # be sure to set the class variable, not the instance variable
    MCR.consoleLogHandler.setLevel(logging.DEBUG)     # However, set the logging level in the instance variable

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
    MCR.consoleLogHandler.setLevel(logging.INFO)     # Reset the logging level in the instance variable
    return MCR


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
    if not MCR.boardInitialized:
        log.error(f'Board did not initialize on {comport}')
        return MCR
    time.sleep(1)

    # new communication path
    log.info('Setting new communications path')
    MCR.MCRBoard.setCommunicationPath('USB')

    # wait >700ms for board to reboot
    time.sleep(1)
    return MCR

def serialPortConnectionLose(comport:str, lensType:str='TL1250'):
    '''
    Example: if the communication to the com port os lost at some point (unintentionally), the MCR module
    will attempt to reconnect to the port.  This may cause a position error in the lens due to the move
    not completing correctly.
    ### input:
    - comport: com port string ('com4' for example)
    - lensType: lens model [TL410 | TL1250]
    '''
    MCR = init(comport, lensType)
    if MCR is None: return None

    # lost connection to the com port (don't do this)
    MCR.serialPort.close()
    log.info(f'Simulating serial port {comport} connection lost')

    # subsequent commands to TheiaMCR will attempt to reconnect to the port
    response = MCR.focus.moveAbs(4000)
    log.info(f'Move response: {"OK" if response == mcr.errList.ERR_OK else response}')
    # check the error list to see if there was a serial port error (check the top level class)
    # Check the error list lastest [-1] error number [0] to match the ERR_SERIAL_PORT error code (-64)
    #  or check for incremented boardCommunicationRestart variable.
    if mcr.errList.finalError[-1][0] == mcr.errList.ERR_SERIAL_PORT:
        log.error(f'Serial port connection error was created: {mcr.errList.finalError}')
    log.info(f'Number of automatic reconnections: {MCR.boardCommunicationRestarts}')
    return MCR


def runTest(test:int, comport:str, lensType:str):
    '''
    Run one example test.  Each example opens the board; the board is closed afterwards so the next test can reopen the com port.
    '''
    log.info(f'---Run test {test}: {tests[test]}')
    MCR = None
    if test == 1:
        MCR = init(comport, lensType, moduleDebugLevel=False)
    elif test == 2:
        MCR = motorConfiguration(comport, lensType)
    elif test == 3:
        MCR = moveMotorsExample(comport, lensType)
    elif test == 4:
        MCR = limits(comport, lensType)
    elif test == 5:
        MCR = closeLogFile(comport, lensType)
    elif test == 6:
        MCR = close(comport)
    ##### special demonstration functions ######
    elif test == 7:
        MCR = viewCommunications(comport)
    elif test == 8:
        print('WARNING: setting the path to UART or I2C disables USB communication until the board is factory reset.')
        if input('Continue? [y/N]: ').strip().lower() == 'y':
            MCR = changeComPathExample(comport)
    elif test == 9:
        MCR = serialPortConnectionLose(comport, lensType)
    release(MCR)


######################
### interactive console setup
######################
def searchComPorts():
    '''
    Search the connected com ports and keep only USB devices (the MCR board connects as a USB virtual com port).
    ### return:
    [list of ListPortInfo objects for USB serial ports]
    '''
    usbPorts = [p for p in sorted(serial.tools.list_ports.comports()) if p.vid is not None]
    for p in usbPorts:
        log.info(f'Port: {p.device}  {p.description} [{p.hwid}]')
    log.info(f'USB port list: {[p.device for p in usbPorts]}')
    return usbPorts

def portNumbers(ports:list) -> dict:
    '''
    Number the ports in the menu using the number at the end of the port name ('COM10' -> 10, '/dev/ttyUSB0' -> 0).
    In Linux different device types can have the same number (/dev/ttyUSB0 and /dev/ttyACM0).  In that case
    the ports are numbered in list order instead.
    ### return:
    - {menu number: ListPortInfo}
    '''
    numbers = []
    for p in ports:
        match = re.search(r'(\d+)$', p.device)
        numbers.append(int(match.group(1)) if match else None)
    if None in numbers or len(set(numbers)) != len(numbers):
        numbers = list(range(1, len(ports) + 1))
    return dict(sorted(zip(numbers, ports), key=lambda item: item[0]))

def selectComPort() -> str:
    '''
    Ask the user to select a USB com port from the list of connected devices.
    ### return:
    - com port string ('COM10' for example)
    '''
    while True:
        usbPorts = searchComPorts()
        portMenu = portNumbers(usbPorts)
        print('\nAvailable USB serial ports:')
        if not usbPorts:
            print('  (none found - check the USB cable)')
        for num, p in portMenu.items():
            print(f'  {num}: {p.device}  {p.description}')
        choice = input('Select a com port (or r: rescan,  q: quit): ').strip()
        if choice.lower() == 'q':
            sys.exit(0)
        if choice.lower() == 'r' or choice == '':
            continue
        if choice.isdigit() and int(choice) in portMenu:
            return portMenu[int(choice)].device
        if not choice.isdigit():
            # manually entered port name (in Linux make sure there is permission to access the port: sudo usermod -a -G dialout $USER)
            return choice
        print(f'Invalid selection "{choice}"')

def selectLensType() -> str:
    '''
    Ask the user to select the lens type.
    ### return:
    - lens type string from lensTypes
    '''
    while True:
        print('\nLens types:')
        for i, lens in enumerate(lensTypes):
            print(f'  {i}: {lens}')
        choice = input(f'Select lens: ').strip()
        if choice.isdigit() and int(choice) < len(lensTypes):
            return lensTypes[int(choice)]
        print(f'Invalid selection "{choice}"')

def selectTests(comport:str, lensType:str):
    '''
    Show the test menu and ask the user to select tests.
    ### return:
    - list of test numbers, or 'c' (change com port), 'l' (change lens), 'q' (quit)
    '''
    while True:
        print('\nSelect test')
        for num, desc in tests.items():
            print(f'  {num:2d}: {desc}')
        choice = input('Select test(s) (or c: change com port,  l: change lens,  q: quit): ').strip().lower()
        if choice in ('c', 'l', 'q'):
            return choice
        try:
            selected = [int(s) for s in choice.replace(',', ' ').split()]
        except ValueError:
            selected = []
        if selected and all(s in tests for s in selected):
            return selected
        print(f'Invalid selection "{choice}"')

def release(MCR):
    '''
    Close the MCR board and release the com port so the next example can open it again.
    '''
    if MCR is None:
        return
    MCR.close()
    del MCR
    gc.collect()
######################

if __name__ == '__main__':
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')

    try:
        comport = selectComPort()
        lensType = selectLensType()
        while True:
            selection = selectTests(comport, lensType)
            if selection == 'q':
                break
            elif selection == 'c':
                comport = selectComPort()
            elif selection == 'l':
                lensType = selectLensType()
            else:
                for test in selection:
                    runTest(test, comport, lensType)
                    time.sleep(0.2)     # let log output finish before showing the menu
    except (KeyboardInterrupt, EOFError):
        print()
    log.info('Done')
