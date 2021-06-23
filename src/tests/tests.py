from datetime import datetime, timedelta
import unittest
import queue
import os
import pathlib
import time
import sys
import shutil
from concurrent.futures.thread import ThreadPoolExecutor


sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

import src.autolisten.recorder as recorder
import src.autolisten.tools as tools


class TestRecorder(unittest.TestCase):
    def test_init(self):
        rec = recorder.RecordAudio(10, recorder.CHANNELS, -1)
        self.assertEqual(rec.sounds_stream.blocksize, recorder.BLOCKSIZE)
        self.assertEqual(rec.sounds_stream.samplerate, recorder.FS)

        self.assertIsInstance(rec.queue, queue.Queue)

        self.assertFalse(rec.sounds_stream.closed)

    def test_record(self):
        rec = recorder.RecordAudio(5, recorder.CHANNELS, -1)
        # this must finish recording before it comes back
        rec.record()
        self.assertFalse(rec.sounds_stream.active)
        self.assertTrue(rec.sounds_stream.closed)

    def test_write(self):
        wr = recorder.WriterStream(5, "test.ogg", recorder.CHANNELS, -1)

        self.assertEqual(wr.sound_file.format, "OGG")
        self.assertEqual(wr.sound_file.channels, recorder.CHANNELS)
        self.assertTrue(wr.sound_file.closed)
        self.assertEqual(wr.sound_file.name, "test.ogg")
        with self.assertRaises(AssertionError):
            recorder.WriterStream(5, "hello", recorder.CHANNELS, -1)
        self.addCleanup(cleanup_files)


class TestTools(unittest.TestCase):
    def test_file_name(self):
        if os.name == "nt":
            file_name = str(tools.get_filename(5, "C:\Home"))
            self.assertTrue(file_name.startswith("C:\Home"))
        else:
            file_name = str(tools.get_filename(5, "/User/Home"))
            print(file_name)
            self.assertTrue(file_name.startswith("/User/Home"))

    def test_format_date(self):
        # Change date depending when test is ran
        self.assertEqual(tools.format_date_now(), "2021-05-28")

    def test_directories(self):

        self.assertTrue(tools.create_directory(pathlib.Path().cwd()))
        time.sleep(1)

        self.assertFalse(tools.cleanup_files(4, os.getcwd()))
        self.assertTrue(tools.cleanup_files(0, os.getcwd()))

    def test_recorder(self):
        with self.assertRaises(AssertionError):
            recorder.Recorder("fdfdfdvre", 5, 0, 3)
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), -45, 0, 3).record()
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), 100, "Hello", 3).record()
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), 1, 0, 32232).record()
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), 10, -211, 30).record()
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), 1, 0, 32232).record()
        with self.assertRaises(AssertionError):
            recorder.Recorder(os.getcwd(), 10, 1, 30).record()


def cleanup_files():
    os.remove(pathlib.Path(os.getcwd() + "/" + "test.ogg"))


def cleanup_dir():
    shutil.rmtree(pathlib.Path(os.getcwd() + "/" + tools.format_date_now()))


class TestCommandLine(unittest.TestCase):
    def test_channels(self):
        recorder.Recorder(
            os.getcwd(), 1, -1, 1, verbose=False, channels=12, background=False
        ).record()
        self.addCleanup(cleanup_dir)

    def test_long(self):
        recorder.Recorder(os.getcwd(), 1, -1, 1).record()
        self.assertEqual(
            len(os.listdir(pathlib.Path(os.getcwd() + "/" + tools.format_date_now()))),
            60,
        )
        self.addCleanup(cleanup_dir)

    def test_really_long(self):
        # Tested as a minute to simulate a long recording of an hour
        rec = recorder.Recorder(os.getcwd(), 1 / 60, -1, 1 / 60, long_recording=True)
        rec.record()
        self.assertEqual(
            len(os.listdir(pathlib.Path(os.getcwd() + "/" + tools.format_date_now()))),
            rec.files,
        )
        self.addCleanup(cleanup_dir)

    def test_background(self):
        rec = recorder.Recorder(os.getcwd(), 0.5, -1, 1, background=True)
        rec.record()
        self.assertEqual(
            len(os.listdir(pathlib.Path(os.getcwd() + "/" + tools.format_date_now()))),
            rec.files,
        )
        self.addCleanup(cleanup_dir)

    def test_sounddevice(self):
        rec = recorder.Recorder(os.getcwd(), 0.5, -1, 1, sound_device=1)
        rec.record()
        self.assertEqual(
            len(os.listdir(pathlib.Path(os.getcwd() + "/" + tools.format_date_now()))),
            rec.files,
        )
        self.addCleanup(cleanup_dir)

    def test_thread_pool(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            tools.create_directory(pathlib.Path.cwd())
            for _ in range(10):
                future = executor.submit(
                    recorder.Recorder.run_stream, 1, os.getcwd(), 2, executor, -1
                )

                self.assertEqual((0, None), future.result())
            executor.shutdown()
        time.sleep(1)
        self.addCleanup(cleanup_dir)


class TestDelayTimer(unittest.TestCase):
    def test_zero_time(self):
        rec = recorder.Recorder(os.getcwd(), 1, -1, 1, delay=5, closest=0)
        date = timedelta(seconds=rec.get_wait_time()) + datetime.now()
        self.assertEqual(date.second, 0)
        self.assertTrue(date.minute % 5 == 0)
        self.assertEqual(rec.filelen, 5 * tools.MINUTE)
        self.assertEqual(rec.filelen, rec.delay * tools.MINUTE)
        self.assertTrue(rec.long_recording)

    def test_closest_time(self):
        rec = recorder.Recorder(os.getcwd(), 1, -1, 1, delay=23, closest=5)
        date = timedelta(seconds=rec.get_wait_time()) + datetime.now()
        self.assertEqual(date.second, 0)
        self.assertTrue(date.minute % 5 == 0)
        self.assertEqual(rec.filelen, 23 * tools.MINUTE)
        self.assertTrue(rec.long_recording)

    def test_delay_error(self):
        with self.assertRaises(recorder.DelayedError):
            recorder.Recorder(os.getcwd(), 1, -1, 1, delay=18, closest=0)


if __name__ == "__main__":
    unittest.main()
