import argparse
import pathlib

import sys
import subprocess
import sounddevice as sd
from concurrent.futures.thread import ThreadPoolExecutor
import soundfile as sf
import numpy as np
import queue
import datetime
from time import sleep
import concurrent.futures
import os

assert np

import shutil

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

    def __init__(self, location: str=None):
        try:
            self.logfile = open(os.path.join(os.getcwd(), "auto.log"), "a")
        except PermissionError:
            self.logfile = open(os.path.join(location, "auto.log"), "a")
    def write(self, message):
        self.logfile.write(message)

    def flush(self):
        self.logfile.flush()

    def close(self):
        self.logfile.close()


class WriteLog(Log):
    """Stdout log writer to the auto.log file and the console."""

    def __init__(self, location: str = None):
        super(WriteLog, self).__init__(location)
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        super().write(message)

    def flush(self):
        super().flush()
        self.terminal.flush()


class ErrorLog(Log):
    """Stderr log writer to auto.log and the stderr write stream."""

    def __init__(self, location: str=None):
        super(ErrorLog, self).__init__(location)
        self.errors = sys.stderr

    def write(self, message):
        self.errors.write(message)
        super().write(message)

    def flush(self):
        super().flush()
        self.errors.flush()


LOG_DATA = queue.Queue()


class ThreadExit(SystemExit):
    """Error to wrap the call for the interpreter to exit from an existing thread. This wil shutdown the entire process and exit gracefully."""


class StatusError(Exception):
    """Error to represent a status within the reading of an audio stream."""


class RecordAudio:
    """Creates an audio instance to record data from the input stream and add it to the queue."""

    def __init__(self, record_time: int, channels: int, device: int):
        """Creates instance of RecordAudio Class creating an input sound stream and making it playable."""
        print("DEVICE:", device)
        self.duration = record_time
        if device == -1:
            self.device = None
        else:
            self.device = device
        try:
            self.sounds_stream: sd.InputStream = sd.InputStream(
                samplerate=FS,
                blocksize=BLOCKSIZE,
                channels=channels,
                dtype=np.int32,
                callback=self.__callback,
                device=self.device,
            )

        except sd.PortAudioError as e:
            # If we cant open an audio stream, quit the program.
            sys.stderr.write("Port Audio Error: %s\n" % e)
            raise e

        self.queue = queue.Queue()

    def record(self):
        """Begin recording a stream.
        Will continue to record until the alloted time has passed and will then stop."""
        if VERBOSE:
            sys.stdout.write(
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Starting Recording...\n"
            )
        with self.sounds_stream:
            sd.sleep(int(self.duration * 1000))

    def __callback(
        self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags
    ):
        """Streaming callback function. Returns None and only adds data to the queue"""

        del frames, time
        # Must have an error if status is true
        if status:
            sys.stderr.write("%s\n" % status)

            # Need a copy and not a reference so we must copy the array.
        self.queue.put(indata.copy())


class WriterStream:
    """Creates a sound file and writes audio data from an input stream to a file of a specified name.
    Requires that files use the .ogg extension.
    """

    def __init__(
        self, record_time: int, filename: pathlib.Path, channels: int, device: int
    ):
        """Creates an instande of the sound file and writes audio data"""
        assert record_time > 0, "ERROR: Time must be greater than 0"
        assert str(filename)[-4:] == ".ogg", "Must create file with ogg."

        self.record: RecordAudio = RecordAudio(record_time, channels, device)
        try:
            self.sound_file: sf.SoundFile = sf.SoundFile(
                filename,
                "x",
                FS,
                CHANNELS,
                sf.default_subtype("OGG"),
                format="OGG",
            )
        except Exception as e:
            raise e from IOError(e)
        self.read_from_queue()

    def read_from_queue(self):
        """Reads data from the recording queue and writes it to the file. Will continue to write until the queue is empty."""
        try:
            with self.sound_file as f:
                self.record.record()
                while not self.record.queue.empty():
                    f.write(self.record.queue.get())
                f.close()
        except IOError as e:
            sys.stderr.write("ERROR: {0}".format(e))
        except Exception as e:
            sys.stderr.write("ERROR: {0}".format(e))


class DelayedError(Exception):
    """
    Raised when the delay specified is not an common divisor of 60.
    """


class Recorder:
    """
    ### Main base start for recorder module.
    """

    def __init__(
        self,
        location: str,
        timeout: int,
        deletion: int,
        filelen: int = 1800,
        verbose=False,
        channels: int = 2,
        background=False,
        long_recording: bool = False,
        sound_device: int = -1,
        delay: int = 0,
        closest: int = 0,
        log_file_location: str = None,
    ):
        """### Main base start for recorder module.
        - location - specifies the location of the file to save the recordings.
        - timeout - specifies the number of minutes before the program should terminate.
        - deletion - specifies whether or not to delete the file folder of recordings specified in days. Default is None
        - filelen - specifies the length of time in seconds that each file should be.
        - verbose - specifies whether the program should output in verbose mode, Default is False.
        - channels - specify the number of audio channels the program should use. Default is 2.
        - background specify whether the program should run as a background process or in the terminal
        - long_recording - specify whether the program should use timeout and filelength in hours and minutes respectively.
        - sound_device - specify the device the program should use.
        - delay - specify the duration of time in mintues for each file length and to begin recording at the nearest multiple on the hour.
        """
        assert os.path.exists(location), "You have not specified a valid path."
        assert timeout > 0, "The timeout must be greater than zero. "
        if delay == 0:
            assert (
                timeout * MINUTE > filelen
            ), "The timeout must be greater than the length of the file."
        assert filelen >= 0, "The file length must be greater than 0"
        assert channels > 0, "The channels must be greater than zero"
        if deletion != -1:
            assert isinstance(deletion, int), "Deletion must be an integer"
            assert deletion > 0, "Deletion must be greater than 0"
            if long_recording:
                assert (
                    days_to_minutes(deletion) < timeout * HOUR
                ), "Deletion must be greater than timeout date"
            else:
                assert (
                    days_to_minutes(deletion) < timeout * HOUR
                ), "Deletion must be greater than timeout date"

        self.background = background

        if self.background:
            sys.stdout = open(os.path.join(os.getcwd(), "auto.log"), "a")
            sys.stderr = open(os.path.join(os.getcwd(), "auto.log"), "a")
            self.verbose = True
        else:
            sys.stdout = WriteLog(log_file_location)
            sys.stderr = ErrorLog(log_file_location)

        self.location = pathlib.Path(location)
        self.deletion = deletion
        self.filelen = filelen
        self.channels = channels
        self.verbose = verbose
        self.long_recording = long_recording
        self.sound_device = sound_device
        self.timeout = timeout
        self.secs_passed = 0
        self.files = 0
        self.delay = delay
        self.closest = closest

        if self.delay != 0:

            self.filelen = delay
            self.long_recording = True

        if self.closest != 0:
            self.delay = closest

        self.curr_date = format_date_now()

        try:
            self.interval: int = int(HOUR / self.delay)
        except ZeroDivisionError:
            pass

        if self.delay != 0:
            if self.interval * self.delay != HOUR and closest == 0:
                raise DelayedError

        if self.long_recording:
            self.filelen *= MINUTE
            self.timeout *= HOUR

        self.location: pathlib.Path = pathlib.Path(location)
        global VERBOSE
        VERBOSE = self.verbose

    def get_wait_time(self):
        """
        If the program is running in delayed mode, returns the appropriate delay in seconds.
        """
        now = datetime.datetime.now()
        closest_minute = now.minute % self.delay
        diff_time = self.delay - closest_minute
        # Return value in seconds
        return diff_time * MINUTE - now.second

    def record(self):
        self.__record_loop()

    def __record_loop(self):
        """
        #### Base loop for the recorder instance.
        #### Instantiates all recording functionality by setting up the loop and beginning records. Used exclusively with the recorder function.
        - Returns: None
        """
        timelong: int
        if self.long_recording:
            timelong = self.timeout / 60
        else:
            timelong = self.timeout

        if self.delay:
            wait_time = self.get_wait_time()
            sys.stdout.write(
                f"The correct start time has not occured yet. Sleeping for {wait_time} seconds.\n"
            )
            sleep(wait_time)

        create_directory(self.location)
        sys.stdout.write(
            f"Starting recordings at {self.location}. Will continue for {int(timelong)} {'hour' if self.long_recording else 'minute'}{'' if timelong  == 1  else 's'}.\n"
        )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # We can count how much time has passed
            while self.secs_passed < self.timeout * MINUTE:
                try:
                    future = executor.submit(
                        self.run_stream,
                        self.filelen,
                        self.location,
                        self.channels,
                        executor,
                        self.sound_device,
                    )
                except RuntimeError as e:
                    sys.stderr.write("ERROR: %s\n" % e)
                    break
                future.add_done_callback(self.get_done)

                if VERBOSE:
                    sys.stdout.write(
                        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} FILE NO. {self.files+1} out of {int(self.timeout*MINUTE/self.filelen)}\n"
                    )
                
                sleep(self.filelen)
                
                self.files += 1
                self.secs_passed += self.filelen
                if self.curr_date != format_date_now():
                    # create new file
                    create_directory(self.location)
                    if self.deletion != -1:

                        executor.submit(
                            cleanup_files, self.deletion, self.location
                        )
                    self.curr_date = format_date_now()
                sys.stdout.flush()
                sys.stderr.flush()
            executor.shutdown()

        if self.secs_passed >= self.timeout * MINUTE:
            sys.stdout.write(
                f"Finished execution. You can now visit your files at {self.location} !\n"
            )

    @staticmethod
    def run_stream(
        time: int,
        directory: str,
        channels: int,
        executor: ThreadPoolExecutor,
        device: int,
    ):

        """Thread ran function that creates an instance of the WriterStream and records the audio until done."""
        dirs = get_filename(time, directory)
        if VERBOSE:
            sys.stdout.write(
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Starting new thread..\n"
            )
        try:
            WriterStream(time, dirs, channels, device)
        except AssertionError as e:
            return (-1, e)
        except sd.PortAudioError as e:
            executor.shutdown(wait=False)
            return (-1, e)
        except Exception as e:
            return (-1, e)
        return (0, None)

    @staticmethod
    def get_done(future: concurrent.futures.Future):
        """Checks the result of the future and writes an error to stderr if necessary"""
        results = future.result()
        if results[0] == -1:
            sys.stderr.write(f"ERROR: {results[1]}\n")

class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(1)

def run_parsers(parser: argparse._SubParsersAction):
    """Parses main programs arguments"""

    no_delay_parser = parser.add_parser(
        "run", help="Runs the main execution of the program"
    )
    delayed = parser.add_parser(
        "delayed",
        help="Runs the main execution of the program delayed",
    )

    delayed.add_argument(
        "delay",
        type=int,
        help="Specifies the nearest start time multiple within the hour.",
    )
    delayed.add_argument(
        "-cl",
        "--closest",
        type=int,
        help="Finds the closest delay value to begin recording.",
        metavar="",
        choices=[1, 2, 3, 4, 5, 10, 12, 15, 20, 30, 60],
    )
    parser_arr = [no_delay_parser, delayed]

    for _parser in parser_arr:

        _parser.add_argument(
            "location",
            help="The location to save the files to. Both Posix and Windows Syntax will work.",
            type=pathlib.Path,
        )
        
        if _parser == no_delay_parser:
            _parser.add_argument(
                "timeout",
                help="The program timeout in minutes to specify when the program will terminate.",
                type=int,
            )
        else:
            _parser.add_argument(
                "timeout",
                help="The program timeout in hours to specify when the program will terminate.",
                type=int,
            )

        if _parser == no_delay_parser:
            _parser.add_argument(
                "-l",
                "--length",
                help="The file length of time in seconds before the program should create a new one. Defaults to 1800 seconds.",
                type=int,
                metavar="",
                default=1800,
            )
        _parser.add_argument(
            "-fl",
            "--file_location",
            help="The location of the logfile.",
            type=pathlib.Path,
        )
        _parser.add_argument(
            "-d",
            "--delete",
            help="Field to specify when to delete an audio file subdirectory in days. Defaults to None.",
            type=int,
            metavar="",
            default=-1,
        )

        _parser.add_argument(
            "-b",
            "--background",
            help="Specify whether the program should run in the background.",
            action="store_true",
        )
        _parser.add_argument(
            "-v",
            "--verbose",
            help="Specify to enter verbose mode.",
            action="store_true",
        )
        _parser.add_argument(
            "-c",
            "--channels",
            help="Specify the number of audio input channels AutoListen should use. Default is 2",
            type=int,
            metavar="",
            default=2,
        )

        if _parser == no_delay_parser:
            _parser.add_argument(
                "-lr",
                "--long_record",
                help="Specify to use long recording mode where the timeout can now be specified in hours and the filelength can be specified in minutes.",
                action="store_true",
            )

        group = _parser.add_mutually_exclusive_group()

        group.add_argument(
            "-dv",
            "--device",
            help="Specify the device you would like to use as an integer. Use 'autolisten devices' to see the available devices.",
            type=int,
            metavar="",
        )
        group.add_argument(
            "-ds",
            "--device_string",
            help="Specify the device you would like to use as a string. Use 'autolisten devices' to see the available devices. NOTE: Use `autolisten -d ` with the device name to ensure it exists.",
            type=str,
            metavar="",
        )

    return _parser


def device_parsers(main_parser: argparse._SubParsersAction):
    """Parses device listings arguments"""
    device_parser = main_parser.add_parser(
        "devices", help="displays the available devices for your system."
    )

    device_parser.add_argument(
        "-a",
        "--all",
        help="displays all available devices for your system",
        action="store_true",
    )
    device_parser.add_argument(
        "-i",
        "--input",
        help="Displays information about default input device",
        action="store_true",
    )
    device_parser.add_argument(
        "-o",
        "--output",
        help="Displays information about default output device",
        action="store_true",
    )

    device_parser.add_argument(
        "-d",
        "--device",
        help="Specify the device name with a substring/string.",
        type=str,
        metavar="",
    )

    return device_parser


def test_parsers(main_parser: argparse._SubParsersAction):
    """Parses test functionality arguments"""
    test_parser = main_parser.add_parser(
        "tests", help="Runs the unit tests associated with the program."
    )
    test_parser.add_argument("--all", help="Runs all unit tests.", action="store_true")
    test_parser.add_argument(
        "-t", "--tools", help="Run tool test suite", action="store_true"
    )
    test_parser.add_argument(
        "-r ", "--recorder", help="Run recorder test suite", action="store_true"
    )
    test_parser.add_argument(
        "-c",
        "--command_line",
        help="Run the command line test suite",
        action="store_true",
    )
    test_parser.add_argument(
        "-dt",
        "--delay_timer",
        help="Run the delay timer test suite",
        action="store_true",
    )
    return test_parser


# Entry point
def main():
    """Main will be responsible for calling and executing the program in recorder.py."""
    parser = MyParser(
        description="AutoListen is a scripting tool to record and separate large amounts of audio."
    )

    main_parser = parser.add_subparsers(help="commands", dest="command")

    device_parser = device_parsers(main_parser)
    run_parsers(main_parser)
    test_parsers(main_parser)

    args = parser.parse_args()

    if args.command == "devices":
        if args.all:
            print(sd.query_devices())
        elif args.input:
            print(sd.query_devices(kind="input"))
        elif args.output:
            print(sd.query_devices(kind="output"))
        elif args.device != "":
            print(args.device)
            print(sd.query_devices(args.device))
        else:
            device_parser.print_help()

    elif args.command == "run" or args.command == "delayed":

        if args.command == "delayed":
            long_record = True
            delay = args.delay
            if args.closest is not None:
                closest = args.closest
            else:
                closest = 0
            length = 0
        else:
            delay = 0
            closest = 0
            length = args.length
            long_record = args.long_record

        
        if args.device is None:
            device = args.device_string
        elif args.device_string is None:
            device = args.device
        else:
            device = None
        

        if args.background:
            p = subprocess.Popen(
                f"{sys.executable} -c \"from src.autolisten.recorder import Recorder; Recorder(r'{args.location}', {args.timeout}, {args.delete}, {length}, {args.verbose}, {args.channels}, {args.background}, {long_record}, {device}, {delay}, {closest}, {args.file_location}).record()\"",
                shell=True,
                close_fds=True,
            )
            print(
                "AutoListen is now runnning as a background process with process id:",
                p.pid,
            )
        else:

            rec = Recorder(
                args.location,
                args.timeout,
                args.delete,
                length,
                args.verbose,
                args.channels,
                long_recording=long_record,
                sound_device=device,
                delay=delay,
                closest=closest,
                log_file_location=args.file_location
            )
            rec.record()

    elif args.command == "tests":
        import src.tests.tests as tests
        import unittest

        if args.recorder:
            suite = unittest.TestLoader().loadTestsFromTestCase(tests.TestRecorder)
        elif args.tools:
            suite = unittest.TestLoader().loadTestsFromTestCase(tests.TestTools)
        elif args.command_line:
            suite = unittest.TestLoader().loadTestsFromTestCase(tests.TestCommandLine)
        elif args.delay_timer:
            suite = unittest.TestLoader().loadTestsFromTestCase(tests.TestDelayTimer)
        else:
            suite = unittest.TestLoader().loadTestsFromModule(tests)

        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

    elif args.command == None:
        parser.print_help()


if __name__ == "__main__":
    main()


