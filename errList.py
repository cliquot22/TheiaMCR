from inspect import currentframe
import logging as log
# global
# store the error here that ends the program.  Read it out for display to the user.  
finalError = []

# common error codes
# error formatted lists are of the form [err code, module, line]

# error codes
ERR_FUNCTION_EXCEPTION = -60
ERR_SN_DATA = -61
ERR_BAD_MOVE = -62
ERR_CURVE_FIT = -63
ERR_SERIAL_PORT = -64
ERR_PARAM = -65
ERR_USER_CANCEL = -66
ERR_COMMAND_ID_MISMATCH = -67
ERR_LIMIT_EXCEEDED = -68
ERR_RANGE = -69
ERR_CANCEL_NOT_ADJUSTED = -70
ERR_MISSING_SETUP_PARAM = -71

# file read errors
ERR_NOT_FOUND = -12                 # file section header not found
ERR_SN_PREFIX = -13                 # serial number prefix not found in file
ERR_SETTINGS_NOT_FOUND = -14        # settings.json file not found - hard exit
ERR_KEY_NOT_FOUND = -15
ERR_FILE_NOT_FOUND = -16            # file was moved or deleted, not found

# MCR errors
ERR_NOT_INIT = -24              
ERR_PI_NOT_INIT = -25
ERR_NO_TRIALS = -26                 # no autofocus trials done
ERR_TOO_FEW_TRIALS = -27            # too few trials for fitting
ERR_FOCUS_NOT_FOUND = -28           # no autofocus peak found before maximum trials
ERR_STEP_LIMIT = -29                # exceeding the maximum number of steps
ERR_FOCUS_PAST_PEAK = -30           # auto focus started past peak
ERR_NO_COMMUNICATION = -31          # no communication/ response from MCR board

# IMHR machine errors
ERR_IMHR_ANGLE = -35                # object angle arm setup error
ERR_IMHR_DIST = -36                 # object distance setup error
ERR_IMHR_FILTER = -37               # filter position setup error
ERR_IMHR_MTF = -38
ERR_IMHR_NOT_READY = -39
ERR_IMHR_NO_RESP = -40
ERR_X_OFFSET = -41
ERR_Y_OFFSET = -42
ERR_IMHR_OTHER = -43    

# communication errors
ERR_TOO_LARGE = -50

# modules
MOD_AF = 1                          # autoFocus.py
MOD_COM = 2                         # commTCPIP.py
MOD_DF = 3                          # dataFormat.py
MOD_LANG = 4                        # language.py
MOD_LD = 5                          # lensData.py
MOD_MC_GUI = 6                      # master control GUI.py
MOD_MC = 7                          # masterControl.py
MOD_MCR = 8                         # MCRControl.py
MOD_SPEC = 9                        # specialTestScript.py
MOD_TP = 10                         # testPlan.py

# save the error in global variables
# global: finalError
# input: errNum: error number
#       modNum: module number that generated the error
#       lineNum: line in the module
def saveError(errNum:int, modNum:int, lineNum:int):
    global finalError
    log.error(f'ERROR: {errNum} {decipher(errNum)} in module {module(modNum)}, ln {lineNum}')
    finalError.append([errNum, modNum, lineNum])

# clear the error list
# global: finalError
def clearErrorList():
    global finalError
    finalError = []

# print the error list to the active log
def printErrorListToLog():
    for error in finalError:
        log.error(f'  {error[0]} {decipher(error[0])}, module {module(error[1])}, line {error[2]}')
    
# decipher
# decipher error number
# input: error number or formatted list
# return: user readable string
def decipher(errNum):
    if isinstance(errNum, list):
        errNum = errNum[0]

    errorList = {\
        # error codes
        ERR_FUNCTION_EXCEPTION: 'captures exception error in the function', \
        ERR_SN_DATA: 'no lens data for scanned serial number', \
        ERR_BAD_MOVE: 'MCR move returned unsuccessful', \
        ERR_CURVE_FIT: 'curve fitting error', \
        ERR_SERIAL_PORT: 'serial port not open', \
        ERR_PARAM: 'function parameter input error', \
        ERR_USER_CANCEL: 'user cancel test before completion', \
        ERR_COMMAND_ID_MISMATCH: 'id mismatch between command and IMHR return value', \
        ERR_LIMIT_EXCEEDED: 'lens or calculation limit exceeded', \
        ERR_RANGE: 'input parameter out of range', \
        ERR_CANCEL_NOT_ADJUSTED: 'user canceled test due to IMHR adjustment issue', \
        ERR_MISSING_SETUP_PARAM: "setup parameter missing, can't start automated testing", \

        # file read errors
        ERR_NOT_FOUND: 'file section header not found', \
        ERR_SN_PREFIX: 'serial number prefix not found in file', \
        ERR_SETTINGS_NOT_FOUND: 'settings.json file not found - hard exit', \
        ERR_KEY_NOT_FOUND: 'key value was not found', \
        ERR_FILE_NOT_FOUND: 'file name not found', \

        # MCR errors
        ERR_NOT_INIT: 'Not initialized', \
        ERR_PI_NOT_INIT: 'Photo interrupter not initialized', \
        ERR_NO_TRIALS: 'no autofocus trials done', \
        ERR_TOO_FEW_TRIALS: 'too few trials for curve fitting', \
        ERR_FOCUS_NOT_FOUND: 'no autofocus peak found before maximum trials', \
        ERR_STEP_LIMIT: 'exceeded maximum number of steps avaialble', \
        ERR_FOCUS_PAST_PEAK: 'autofocus started past peak', \
        ERR_NO_COMMUNICATION: 'no communication/ response from MCR board', \
        
        # IMHR machine errors
        ERR_IMHR_ANGLE: 'IMHR object angle arm setup error', \
        ERR_IMHR_DIST: 'IMHR object distance setup error', \
        ERR_IMHR_FILTER: 'IMHR filter position setup error', \
        ERR_IMHR_MTF: 'IMHR MTF measurement error', \
        ERR_IMHR_NOT_READY: 'IMHR Not ready to communicate', \
        ERR_IMHR_NO_RESP: 'IMHR did not send a response to the command', \
        ERR_X_OFFSET: 'IMHR X position of cross is off sensor area', \
        ERR_Y_OFFSET: 'IMHR Y position of cross is off sensor area', \
        ERR_IMHR_OTHER: 'IMHR other error', \

        # communication errors
        ERR_TOO_LARGE: 'Number too large', \
    }

    return errorList[errNum]


# decipher module generating error code
# input: module number constant or error code list
# return: module name string
def module(modNum):
    if isinstance(modNum, list):
        modNum = modNum[1]
    modList = { \
        MOD_AF: 'autoFocus.py', \
        MOD_COM: 'commTCPIP.py', \
        MOD_DF:  'dataFormat.py', \
        MOD_LANG: 'language.py', \
        MOD_LD: 'lensData.py', \
        MOD_MC_GUI: 'master control GUI.py', \
        MOD_MC: 'masterControl.py', \
        MOD_MCR: 'MCRControl.py', \
        MOD_SPEC: 'specialTestScript.py', \
        MOD_TP: 'testPlan.py', \
    }

    return modList[modNum]

# get line number when generating an error code
def errLine():
    global finalErrorLine
    cf = currentframe()
    finalErrorLine = cf.f_back.f_lineno
    return finalErrorLine