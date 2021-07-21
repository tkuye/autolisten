import argparse
import pathlib

import sys
import subprocess
import sounddevice as sd

from .recorder import Recorder


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(1)


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
    delete_parser(main_parser)

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
                f"{sys.executable} -c \"from src.autolisten.recorder import Recorder; Recorder(r'{args.location}', {args.timeout}, {args.delete}, {length}, {args.verbose}, {args.channels}, {args.background}, {long_record}, {device}, {delay}, {closest}).record()\"",
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
            )
            rec.record()

    elif args.command == "delete":
        import src.autolisten.delete as delete

        delete.delete_folders(args.location, args.days)

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
        elif args.deletion:
            suite = unittest.TestLoader().loadTestsFromTestCase(tests.TestDeletion)
        else:
            suite = unittest.TestLoader().loadTestsFromModule(tests)

        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

    elif args.command == None:
        parser.print_help()


if __name__ == "__main__":
    main()

def delete_parser(parser: argparse._SubParsersAction):
    """Parses the delete programs arguments"""

    del_parser = parser.add_parser(
        "delete",
        help="Responsible for deleting the files of a given folder older than a certain date.",
    )

    del_parser.add_argument(
        "days",
        type=int,
        default=0,
        help="To specify how old the files are. Default is 0.",
    )

    del_parser.add_argument(
        "location", type=pathlib.Path, help="Where the files are located."
    )


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
    test_parser.add_argument(
        "-dl",
        "--deletion",
        help="Run the deletion test suite",
        action="store_true",
    )
    return test_parser
