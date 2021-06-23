from concurrent.futures.thread import ThreadPoolExecutor
import sounddevice as sd
import soundfile as sf
import numpy as np
import sys
import queue
import datetime
from time import sleep
import concurrent.futures
import os
import pathlib
import src.autolisten.tools as tools


assert np

from src.autolisten.tools import (
    CHANNELS,
    ErrorLog,
    VERBOSE,
    FS,
    MINUTE,
    BLOCKSIZE,
    HOUR,
)


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
                    tools.days_to_minutes(deletion) < timeout * HOUR
                ), "Deletion must be greater than timeout date"
            else:
                assert (
                    tools.days_to_minutes(deletion) < timeout * HOUR
                ), "Deletion must be greater than timeout date"

        self.background = background

        if self.background:
            sys.stdout = open(os.path.join(os.getcwd(), "auto.log"), "a")
            sys.stderr = open(os.path.join(os.getcwd(), "auto.log"), "a")
            self.verbose = True
        else:
            sys.stdout = tools.WriteLog()
            sys.stderr = tools.ErrorLog()

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

        self.curr_date = tools.format_date_now()

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

        tools.create_directory(self.location)
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
                if self.curr_date != tools.format_date_now():
                    # create new file
                    tools.create_directory(self.location)
                    if self.deletion != -1:

                        executor.submit(
                            tools.cleanup_files, self.deletion, self.location
                        )
                    self.curr_date = tools.format_date_now()
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
        dirs = tools.get_filename(time, directory)
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
