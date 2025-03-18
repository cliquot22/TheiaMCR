# Rotating log file handler for Python logging
# This class creates a rotating log file handler that alternates between two log files.
# Mark Peterson (c) 2025
# Program revisions
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
    revision = 'v.1.0.0'
    
    def __init__(self, logger, maxLines:int=10000):
        '''
        This class creates a rotating log file handler that alternates between two log files.
        ### input:  
        - logger: the logger instance to which this handler will be added
        - maxLines: the maximum number of lines in each log file before it rotates to the next log file
        ### public functions:  
        close(): this closes and cleans the file logging.  This should be called before ending the program.  
        '''
        super().__init__()
        self.logger = logger
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d,%(levelname)-7s,%(lineno)-5d,%(module)-10s,%(message)s','%y%m%d,%H:%M:%S')
        self.setFormatter(formatter) #set formatter on the handler
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self) #add the handler to the logger

        self.filenames = self.createLogFilenames()
        self.maxLogFileLines = maxLines
        self.currentLogFileNum = 0  # 0 or 1, indicating which file is active
        self.currentLogFileLine = 0
        self.fileHandles = [None, None]  # Store file handles for both files

        # open the first log file
        self.rotate()
        print(f'Log files created in {os.path.dirname(self.filenames[0])}')

    def emit(self, record:str):
        '''
        Write the log record. 
        ### input:  
        - record: the log record to be written to the log file
        '''
        # check if the log file is available
        if self.fileHandles[self.currentLogFileNum] is None:
            return 
        # write into the log file
        try:
            msg = self.format(record)
            self.fileHandles[self.currentLogFileNum].write(msg + '\n')
            self.currentLogFileLine += 1
            if self.currentLogFileLine >= self.maxLogFileLines:
                self.rotate()
        except Exception:
            self.handleError(record)
        return

    # Find file paths based on development or deployment.  
    def createLogFilenames(self) -> list[str]:
        '''
        Set the base path of the AppData/Local (Windows) or .local/share (Linux) or development folder. 
        Return 2 log file names for rolling log file.
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

        # create the rotating log file names
        logA = os.path.join(basePath, "logA.txt")
        logB = os.path.join(basePath, "logB.txt")
        self.logFolderPath = basePath
        return logA, logB

    def rotate(self):
        '''
        Close one log file (if it is open) and switch to the other file. 
        '''
        if self.fileHandles[self.currentLogFileNum]:
            self.fileHandles[self.currentLogFileNum].close()
        self.currentLogFileNum = 1 - self.currentLogFileNum

        # Check if file exists, create if it doesn't
        if not os.path.exists(self.filenames[self.currentLogFileNum]):
            open(self.filenames[self.currentLogFileNum], 'w').close()

        self.fileHandles[self.currentLogFileNum] = open(self.filenames[self.currentLogFileNum], 'w')
        self.currentLogFileLine = 0

    def close(self):
        ''' 
        Close logging file handles and remove handler from logger.
        '''
        self.acquire()
        try:
            if self.fileHandles[0]:
                self.fileHandles[0].close()
            if self.fileHandles[1]:
                self.fileHandles[1].close()
            self.fileHandles = [None, None]
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
    handler = rotatingLogFiles(log, maxLines=5) #example with 5 lines

    for i in range(12):
        log.info(f"Log entry {i}")
    handler.close()

    log.info('Back to console logging.  Check the log files in the log folder to see a maximum of 5 lines.')
