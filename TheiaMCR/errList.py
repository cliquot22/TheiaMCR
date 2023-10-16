from inspect import currentframe
import logging as log
# global
# store the error here that ends the program.  Read it out for display to the user.  
finalError = []

# common error codes
# error formatted lists are of the form [err code, module, line]

# error codes
ERR_BAD_MOVE = -62                  # MCR move returned unsuccessful
ERR_SERIAL_PORT = -64               # serial port not open
ERR_RANGE = -69                     # input parameter out of range
ERR_NOT_INIT = -24                  # Not initialized
ERR_NO_COMMUNICATION = -31          # no communication/ response from MCR board
ERR_MOVE_TIMEOUT = -32              # no response before timeout

# modules
MOD_MCR = 8                         # MCRControl

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
# input: error number or formatted error code list type
# return: user readable string
def decipher(errNum):
    if isinstance(errNum, list):
        errNum = errNum[0]
    
    errorList = {
        # error codes
        ERR_BAD_MOVE: 'MCR move returned unsuccessful', 
        ERR_SERIAL_PORT: 'serial port not open', 
        ERR_RANGE: 'input parameter out of range', 
        ERR_NOT_INIT: 'Not initialized', 
        ERR_NO_COMMUNICATION: 'no communication/ response from MCR board', 
        ERR_MOVE_TIMEOUT: 'no response before timeout'
    }
    return errorList[errNum]


# decipher module generating error code
# input: module number constant or error code list type
# return: module name string
def module(modNum):
    if isinstance(modNum, list):
        modNum = modNum[1]
    modList = { 
        MOD_MCR: 'MCRControl.py'
    }
    return modList[modNum]

# get line number from the code when generating an error code
def errLine():
    global finalErrorLine
    cf = currentframe()
    finalErrorLine = cf.f_back.f_lineno
    return finalErrorLine