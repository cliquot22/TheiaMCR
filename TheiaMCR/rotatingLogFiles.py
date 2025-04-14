# Rotating log file handler for Python logging
# This class creates a rotating log file handler that alternates between two log files.
# Mark Peterson (c) 2025

# Program revisions
# v.1.0.1 250319 existing log files can be appended, not overwritten
# v.1.0.0 250311

import logging
import os
import errno

class rotatingLogFiles(logging.Handler):
    '''
    Create a rotating log file handler that alternates between two log files.

    Set up and use:  
    log = logging.getLogger(__name__)   # set up a logger
    logging.basicConfig(level=logging.INFO, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')    # define the basic log format for streaming console
    handler = rotatingLogFiles(log)   # create the rotating log file handler
    # close the files and release the handler when done
    handler.close()
    '''
    revision = 'v.1.0.1'
    
    def __init__(self, logger, nameKey:str='', maxLines:int=10000):
        '''
        This class creates a rotating log file handler that alternates between two log files.
        ### input:  
        - logger: the logger instance to which this handler will be added
        - nameKey: the key to be used in the log file name (default is empty string)
        - maxLines: the maximum number of lines in each log file before it rotates to the next log file
        ### public functions:  
        close(): this closes and cleans the file logging.  This should be called before ending the program.  
        '''
        super().__init__()
        self.logger = logger
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d,%(levelname)-7s,%(lineno)-5d,%(module)-10s,%(message)s','%y%m%d,%H:%M:%S')
        self.setFormatter(formatter) 
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self)

        self.filenames = self.createLogFilenames(nameKey)
        # check for errors in file creation
        if self.filenames == [None, None]:
            ################ do something
            pass

        self.maxLogFileLines = maxLines
        self.currentLogFileNum = 0  # 0 or 1, indicating which file is active
        self.currentLogFileLine = 0
        self.fileHandle = None

        # open the first log file
        self.fileHandle, self.currentLogFileLine = self.openLogFile(self.filenames[0])
        if self.currentLogFileLine >= self.maxLogFileLines:
            self.fileHandle, self.currentLogFileLine = self.rotate()
                
        self.fileHandle.write('---------- module startup ----------------\n')

    def emit(self, record:str):
        '''
        Write the log record. 
        ### input:  
        - record: the log record to be written to the log file
        '''
        # check if the log file is available
        if self.fileHandle is None:
            return 
        # write into the log file
        try:
            msg = self.format(record)
            self.fileHandle.write(msg + '\n')
            self.currentLogFileLine += 1
            if self.currentLogFileLine >= self.maxLogFileLines:
                self.fileHandle, self.currentLogFileLine = self.rotate()
        except Exception:
            self.handleError(record)
        return

    # Find file paths based on development or deployment.  
    def createLogFilenames(self, nameKey:str='') -> list[str]:
        '''
        Set the base path of the AppData/Local (Windows) or .local/share (Linux) or development folder. 
        Return 2 log file names for rolling log file.
        ### input:  
        - nameKey: the key to be used in the log file name (default is empty string)
        ### return: 
        [AppData/Local/TheiaMCR/log/logA.txt, ...logB.txt] or 
        [.local/share/TheiaMCR/log/logA.txt, ...logB.txt]
        '''
        if os.name == 'nt':  # Windows
            appDataPath = os.getenv('LOCALAPPDATA')
            if appDataPath is None:
                # Handle the case where LOCALAPPDATA is not set (rare)
                print("LOCALAPPDATA environment variable not set. Using current directory.")
                appDataPath = os.getcwd() #use current directory if no env variable
            basePath = os.path.join(appDataPath, 'TheiaMCR', 'log')
        else:  # Linux, macOS, etc.
            appDataPath = os.path.expanduser('~/.local/share')
            basePath = os.path.join(appDataPath, 'TheiaMCR', 'log')

        try:
            # Create the "TheiaMCR" and "log" directories if they don't exist
            os.makedirs(basePath, exist_ok=True) # use makedirs to create both folders in one call, and exist_ok to prevent errors if they already exist.
        except OSError as e:
            if e.errno == errno.EACCES:
                # Permission error for creating the folder
                print(f'Permission error creating the log folder: {e}')
                return [None, None]
            else:
                # other OS error
                print(f'Error creating log files: {e}')
                return [None, None]

        nameKey = nameKey.strip('\\/').split('\\')[-1].split('/')[-1]
        # create the rotating log file names
        logA = os.path.join(basePath, f"logA-{nameKey}.txt")
        logB = os.path.join(basePath, f"logB-{nameKey}.txt")
        return logA, logB

    def rotate(self):
        '''
        Close one log file (if it is open) and switch to the other file. 
        ### return:  
        [  
        - file handle,  
        - line number  
        ]
        '''
        self.currentLogFileNum = 1 - self.currentLogFileNum
        handle, length = self.openLogFile(self.filenames[self.currentLogFileNum])
        if length >= self.maxLogFileLines:
            # reset the file
            open(self.filenames[self.currentLogFileNum], 'w').close()
            length = 0
        return handle, length

    def openLogFile(self, filename:str):
        '''
        Open the log file.  
        ### input:  
        - filename: the file path to open
        ### return:  
        [  
        - file handle,  
        - line number  
        ]
        '''
        # Check if file exists
        if not os.path.exists(filename):
            # Create a new file
            open(filename, 'w').close()
            handle = open(filename, 'w')
            return handle, 0
        
        # open an existing file and check the length
        logLength = 0
        try:
            with open(filename, 'r') as file:
                logLength = len(file.readlines())
        except Exception as e:
            # not able to open (corrupted file?),  delete the log file
            try:
                os.remove(filename)
                logLength = 0
            except Exception as delete_error:
                print(f"Error deleting {filename}: {delete_error}")
                return None, -1

        handle = open(filename, 'a')
        return handle, logLength
    
    def close(self):
        ''' 
        Close logging file handles and remove handler from logger.
        '''
        self.acquire()
        try:
            if self.fileHandle:
                self.fileHandle.close()
            self.fileHandle = None
            self.logger.removeHandler(self)
        finally:
            self.release()
        logging.Handler.close(self)


###################################################
### Demonstration of the class functions ##########
###################################################
if __name__ == "__main__":
    # logging setup
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)-7s ln:%(lineno)-4d %(module)-18s  %(message)s')
    
    log.info('Started console logging')
    handler = rotatingLogFiles(log, maxLines=10) #example with 10 lines

    for i in range(12):
        log.info(f"Log entry {i}")
    handler.close()

    log.info('Back to console logging.  Check the log files in the log folder to see a maximum of 10 lines.')
