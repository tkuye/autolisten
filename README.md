# AutoListen

AutoListen is a scripting tool to record and separate large amounts of audio. 

## Basic Setup 

Please ensure that portaudio is installed. Go to [portaudio](http://files.portaudio.com/download.html) to download. 

1. Begin by running: 
 ```
 $ pip install pipenv
 $ pipenv install -e .
 ```
This will install all the required dependencies for the program.

2. Then run
```
$ pipenv shell
```
This will activate the shell virtual environment and you can now install the prgram setup files.

You can now use  `autolisten -h` to list all the commands. 


## Example Commands

All operations will use the `autolisten` command. Using the command line, specify the default location to save the files to and a program timeout in **minutes**. You may also provide the audio file length in **seconds** using the `-l` argument. If this is missing, the file length will default to 30 minutes. 


##### `$ autolisten run C:\User\Local\Desktop 604800 -l 3600 `

- The first argument specifies the location to save the file to. In this case it's `C:\User\Local\Desktop`.
- The second argument specifies the length of time before the program timeout. In this case it's 604800 minutes or 1 week. 
- The `-l` argument specifies how long each length of footage should be. In this case it's 3600 seconds or 1 hour. 

```
$ autolisten run C:\User\Local\Desktop  604800 -d 86400 -b
Starting recordings at C:\User\Local\Desktop. Will continue for 604800 minute(s).
AutoListen is now runnning as a background process with process id: 12132
```



- You may additionally use the `-b` argument to have the program run as a background process. The program will continue running after you close the terminal or the window. The command will provide the process id to view the process inn action. 

- The `-d` argument specifies the length of time in days before the folder containing files should be deleted. This defaults to None. 

```
$ autolisten run C:\User\Local\Desktop  604800 -d 86400 -v
Starting recordings at C:\User\Local\Desktop. Will continue for 604800 minute(s).
Creating directory at location C:\User\Local\Desktop
2021-05-21 10:23:12 starting new thread..
2021-05-21 10:23:12 Starting Recording...
2021-05-21 10:23:12 File NO. 1 of 20160
```

- The `-v` argument specifies to enter verbose mode to display all processes as they occur. 

- The `-lr` argument also known as long record mode uses minutes for the file length and hours for the timeout. 


Autolisten can also run in delayed mode to ensure that the file recordings don't begin until a specified time. 

For example 
```
$ autolisten delayed 3  C:/Users/toskuy/Desktop/autolisten 1 --verbose
```
This command would create a file length of three minutes and begin running on the nearest common multiple of 3 minutes on the hour.
- If the time were 12:46, the files would begin recording at 12:48.

You can also use the `--closest` command and choose a common multiple of an hour to start and specify any file length. 

```
 autolisten delayed 3  C:/Users/toskuy/Desktop/autolisten 1 --verbose --closest 15
```

This command would start recording at the nearest multiple of 15 minutes. 

- You can additionally view what available devices are on your computer using `autolisten devices --all.`
```
$ autolisten devices --all
1 Microphone Array (Realtek High , MME (2 in, 0 out)
2 Microsoft Sound Mapper - Output, MME (0 in, 2 out)
3 Speaker/HP (Realtek High Defini, MME (0 in, 2 out)
4 Primary Sound Capture Driver, Windows DirectSound (2 in, 0 out)
5 Microphone Array (Realtek High Definition Audio), Windows DirectSound (2 in, 0 out)
6 Primary Sound Driver, Windows DirectSound (0 in, 2 out)
7 Speaker/HP (Realtek High Definition Audio), Windows DirectSound (0 in, 2 out)
8 Speaker/HP (Realtek High Definition Audio), Windows WASAPI (0 in, 2 out)
9 Microphone Array (Realtek High Definition Audio), Windows WASAPI (2 in, 0 out)
10 Microphone Array (Realtek HD Audio Mic input), Windows WDM-KS (2 in, 0 out)
11 Speakers (Realtek HD Audio output), Windows WDM-KS (0 in, 2 out)
```
- To display information about your default input and output devices for your system use:
`autolisten devices --input ` or `autolisten devices --output`


- To run the test suites, specify `autolisten tests` to run all the test suites.
- For example: To run the tools test suite specify `autolisten tests --tools`. 
Use `autolisten tests --help` to see all the test suites.


#### AutoListen Run
```
usage: autolisten run [-h] [-l] [-d] [-b] [-v] [-c] [-lr] [-dv] location timeout

positional arguments:
  location            The location to save the files to. Both Posix and Windows Syntax will work.
  timeout             The program timeout in minutes to specify when the program will terminate.

optional arguments:
  -h, --help          show this help message and exit
  -l , --length       The file length of time in seconds before the program should create a new one. Defaults to 1800 seconds.
  -d , --delete       Field to specify when to delete an audio file subdirectory in days. Defaults to None.
  -b, --background    Specify whether the program should run in the background.
  -v, --verbose       Specify to enter verbose mode.
  -c , --channels     Specify the number of audio input channels AutoListen should use. Default is 2
  -lr, --long_record  Specify to use long recording mode where the timeout can now be specified in hours and the filelength can be specified in minutes.
  -dv , --device      Specify the device you would like to use. Use 'autolisten devices' to see the available devices.
```

#### Autolisten Delayed
```
usage: autolisten delayed [-h] [-cl] [-d] [-b] [-v] [-c] [-lr] [-dv] delay location timeout

positional arguments:
  delay               Specifies the nearest start time multiple within the hour.
  location            The location to save the files to. Both Posix and Windows Syntax will work.
  timeout             The program timeout in minutes to specify when the program will terminate.

optional arguments:
  -h, --help          show this help message and exit
  -cl , --closest     Finds the closest delay value to begin recording.
  -d , --delete       Field to specify when to delete an audio file subdirectory in days. Defaults to None.
  -b, --background    Specify whether the program should run in the background.
  -v, --verbose       Specify to enter verbose mode.
  -c , --channels     Specify the number of audio input channels AutoListen should use. Default is 2
  -lr, --long_record  Specify to use long recording mode where the timeout can now be specified in hours and the filelength can be specified in minutes.
  -dv , --device      Specify the device you would like to use. Use 'autolisten devices' to see the available devices.
```

#### AutoListen Devices

```
usage: autolisten devices [-h] [-a] [-i] [-o]

optional arguments:
  -h, --help    show this help message and exit
  -a, --all     displays all available devices for your system
  -i, --input   Displays information about default input device
  -o, --output  Displays information about default output device
```

#### AutoListen Tests
```
usage: autolisten tests [-h] [--all] [-t] [-r]

optional arguments:
  -h, --help       show this help message and exit
  --all            Runs all unit tests.
  -t, --tools      Run tool test suite
  -r , --recorder  Run recorder test suite
  -c, --command_line Run the command_line test suite
```



## More Information
1. Autolisten will save all information specified in verbosity mode to a log file named auto.log in the current working directory. 
2. Due to the required use of audio ports on the input system, when using software such as remote desktop, ensure that remote audio play is _disabled_ as there may be difficulties otherwise.

