import shutil
import os
import pathlib
import datetime
import sys

# specifies the number of audio channels to use: Default is 2
CHANNELS = 2
# specifies the Frame rate of teh audio file in Hertz
FS = 44100
# specifies the size of each block of audio data to be read.
BLOCKSIZE = 1024

MINUTE = 60
HOUR = 60

# Used to Identify the command line argument for the mode of the program
VERBOSE = False
# Octal signature for full read write execute permissions
FULL_READ_WRITE_PERMISSIONS = 0o777


def days_to_minutes(days: int):
    """Converts days to minutes."""
    return days * 1440


def create_directory(location: pathlib.Path) -> bool:
    """Creates a directory in a given location. Returns true on success and false on failure"""

    path = str(location / format_date_now())
    if VERBOSE:
        print(
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Creating directory at location {path}"
        )
    try:
        os.mkdir(path, mode=FULL_READ_WRITE_PERMISSIONS)
        os.chmod(path, FULL_READ_WRITE_PERMISSIONS)
    except FileExistsError:
        return False
    else:
        return True


def cleanup_files(since: int, location: str) -> bool:
    """Deletes a directory after a given number of days.
    \nReturns true on success and false on failure"""

    date = datetime.datetime.now()

    file = pathlib.PurePath(
        location + "/" + format_date(date - datetime.timedelta(days=since))
    )
    if VERBOSE:
        print(
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Deleting file at location {file}"
        )
    try:
        shutil.rmtree(str(file))
    except FileNotFoundError:
        return False
    else:
        return True


def format_date_now() -> str:
    """Formats the date and time according to `%Y-%m-%d` format."""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def format_date(date: datetime = datetime.datetime):
    return date.strftime("%Y-%m-%d")


def get_filename(record_time: int, directory: str) -> pathlib.Path:
    """Get the name of the file to record to based on the current date and a directory."""

    assert record_time > 0, "ERROR: Recording time must be greater than 0"

    return pathlib.Path(
        f"{directory}/{format_date_now()}/{datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')}--{(datetime.datetime.now() + datetime.timedelta(seconds=record_time)).strftime('%H-%M-%S')}.ogg"
    )


class Log(object):
    """Base Class for both logging and writing to the console and the log file."""

    def __init__(self):

        self.logfile = open(os.path.join(os.getcwd(), "auto.log"), "a")

    def write(self, message):

        self.logfile.write(message)

    def flush(self):
        self.logfile.flush()

    def close(self):
        self.logfile.close()


class WriteLog(Log):
    """Stdout log writer to the auto.log file and the console."""

    def __init__(self):
        super(WriteLog, self).__init__()
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        super().write(message)

    def flush(self):
        super().flush()
        self.terminal.flush()


class ErrorLog(Log):
    """Stderr log writer to auto.log and the stderr write stream."""

    def __init__(self):
        super(ErrorLog, self).__init__()
        self.errors = sys.stderr

    def write(self, message):
        self.errors.write(message)
        super().write(message)

    def flush(self):
        super().flush()
        self.errors.flush()
