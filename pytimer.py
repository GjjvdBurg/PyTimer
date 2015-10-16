#!/usr/bin/env python3

"""
Simple timer application which:
    - shows a clock with the current time
    - shows the state of the timer as running or paused, colored green or red 
      respectively
    - allows for naming timers
    - saves timers in app directory as log and as json with last timer value
    - allows for loading past timers and continuing timing
    - shows help with 'h' key
    - switches timer state on spacebar press
    - shows how much time currently elapsed on timer

UI:

            Timer Title
            ===========

    Past sessions:
    Start Date\tStart Time\tEnd Date\tEnd Time\tElapsed Time\n
    ----------\t----------\t--------\t--------\t------------\n
    %Y/%m/%d\t%H:%M:%S\t%H:%M:%S\t%Y/%m/%d\t%H:%M:%S\n\n
    STATE\tElapsed Time\tTotal Elapsed\tCurrent Time\n
    -----\t------------\t-------------\t------------\n
    RUNNING\t%H:%M:%S\t%H:%M:%S\t%H:%M:%S\r

"""

from __future__ import print_function, division

import argparse
import datetime
import dateutil.parser
import json
import os
import readchar
import signal
import shutil
import sys
import time
import threading

from termcolor import colored, cprint

APPNAME = 'PyTimer'
EPOCH = datetime.datetime.utcfromtimestamp(0)

def _(a):
    cprint(a, 'magenta')

class Clock(object):

    def __init__(self):
        self.running = False
        self.state_string = ''
        self.die = False

    def run(self):
        self.running = True

    def start(self):
        while not self.die:
            if self.running:
                self.show_time()
            time.sleep(1)

    def stop(self):
        self.die = True

    def show_time(self):
        dt = datetime.datetime.now()
        msg = '        '.join([self.state_string,
            dt.strftime('%H:%M:%S')])
        size = shutil.get_terminal_size()
        msg += ' '*(size.columns - len(msg))
        sys.stdout.write("{}\r".format(msg))
        sys.stdout.flush()

class Timer(object):

    def __init__(self, title):
        self.is_running = False
        self.total_seconds = 0
        self.seconds = 0
        self.time = datetime.datetime.now()
        self.start_time = None
        self.end_time = None
        self.clock = None
        self.title = title
        self.thread = None
        self.max_hdr_len = 0
        self.max_lhdr_len = 0

        if title is None:
            title = self.ask_title()
            if title is None:
                epoch = (datetime.datetime.now() - EPOCH).total_seconds()
                title = str(epoch)

        self.log_file = self.get_logfile()
        self.json_file = self.get_jsonfile()
        self.start()

    def get_logfile(self):
        fname = ('%s/pytimer_%s.log' % (get_logdir(),
            self.title.lower().replace(' ', '_')))
        return fname

    def get_jsonfile(self):
        fname = ('%s/%s_pytimer.json' % (get_logdir(),
            self.title.lower().replace(' ', '_')))
        return fname

    def log_state(self, msg):
        epoch_secs = (datetime.datetime.now() - EPOCH).total_seconds()
        with open(self.log_file, 'a') as fid:
            fid.write('%i: %s\n' % (epoch_secs, msg))

    def log_json(self):
        if self.start_time is None or self.end_time is None:
            return
        data = {'start_time': self.start_time.strftime('%c'),
                'end_time': self.end_time.strftime('%c'),
                'title': self.title}
        with open(self.json_file, 'a') as fid:
            json.dump(data, fid, sort_keys=True)
            fid.write('\n')

    def start_clock(self):
        self.clock = Clock()
        self.thread = threading.Thread(target=self.clock.start)
        self.thread.start()

    def stop_clock(self):
        self.clock.stop()
        self.thread.join()

    def start(self):
        self.print_title()
        self.start_clock()

    def stop(self):
        if self.is_running:
            self.switch()
            time.sleep(1)
        self.stop_clock()

    def run(self):
        self.print_state_header()
        self.switch()
        self.clock.run()
        while True:
            k = readchar.readkey()
            if k == ' ':
                self.switch()
            if k == 'q':
                raise SystemExit

    def switch(self):
        print()
        if self.is_running:
            diff = datetime.datetime.now() - self.time
            self.seconds += diff.total_seconds()
            self.time = datetime.datetime.now()
            self.end_time = datetime.datetime.now()
            self.log_json()
        else:
            self.time = datetime.datetime.now()
            self.start_time = datetime.datetime.now()
        self.is_running = not self.is_running
        state = self.set_state()
        self.log_state(state)

    def ask_title(self):
        qry = input("Enter timer name: ")
        if not qry.strip():
            self.title = None
            _("Using unnamed timer.")
        else:
            self.title = qry.strip()
            _("Using timer name: {}".format(self.title))

    def print_title(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        title = 'Timer: ' + self.title
        titlelen = len(title)
        dsh = ''.join(['=']*titlelen)
        msg = '{}\n{}\n'.format(title, dsh)
        cprint(msg, 'blue')

    def set_state(self):
        if self.is_running:
            state = colored('RUNNING', 'green') + ' '*(self.max_hdr_len - 7)
        else:
            state = colored('HALTED', 'red') + ' '*(self.max_hdr_len - 6)
        elaps = self.string_from_seconds(self.seconds)
        elaps += ' '*(self.max_hdr_len - len(elaps))
        total = self.string_from_seconds(self.total_seconds + self.seconds)
        total += ' '*(self.max_hdr_len - len(total))
        elem = [state, elaps, total]
        msg = '        '.join(elem)
        self.clock.state_string = msg
        return msg

    def print_state_header(self):
        elem = ['State', 'Elapsed', 'Total Elapsed', 'Current Time']
        self.max_hdr_len = max([len(x) for x in elem])
        elem = [x + ' '*(self.max_hdr_len - len(x)) for x in elem]
        dash = ['-'*len(x) for x in elem]
        hdr = '        '.join(elem)
        dsh = '        '.join(dash)
        msg = '\n'.join([hdr, dsh])
        cprint(msg, 'yellow', end='')

    def print_loaded_header(self):
        elem = ['Start Date', 'Start Time', 'End Date', 'End Time',
                'Elapsed Time']
        self.max_lhdr_len = max([len(x) for x in elem])
        elem = [x + ' '*(self.max_lhdr_len - len(x)) for x in elem]
        dash = ['-'*len(x) for x in elem]
        hdr = (' '*8).join(elem)
        dsh = (' '*8).join(dash)
        msg = '\n'.join([hdr, dsh])
        cprint(msg, 'yellow')

    def print_loaded_line(self, start_t, end_t, seconds):
        elem = [start_t.strftime('%Y-%m-%d'), start_t.strftime('%H:%M:%S'),
                end_t.strftime('%Y-%m-%d'), end_t.strftime('%H:%M:%S'),
                self.string_from_seconds(seconds)]
        elem = [x + ' '*(self.max_lhdr_len - len(x)) for x in elem]
        msg = (' '*8).join(elem)
        cprint(msg, 'white')

    def string_from_seconds(self, seconds):
        hours = seconds // 3600
        minutes = (seconds - 3600*hours) // 60
        seconds = (seconds % 60) // 1
        return '%02i:%02i:%02i' % (hours, minutes, seconds)

    @classmethod
    def load_json(cls, filename):
        with open(filename, 'r') as fid:
            lines = fid.readlines()
        title = json.loads(lines[0])['title']
        timer = cls(title)
        timer.print_loaded_header()
        for line in lines:
            data = json.loads(line)
            start_t = dateutil.parser.parse(data['start_time'])
            end_t = dateutil.parser.parse(data['end_time'])
            seconds = (end_t - start_t).total_seconds()
            timer.total_seconds += seconds
            timer.print_loaded_line(start_t, end_t, seconds)
        print()
        return timer

def get_logdir():
    dirname = os.path.expanduser(os.path.join('~', '.' + APPNAME))
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname

def choose_timer():
    files = os.listdir(get_logdir())
    timer_files = [x for x in files if x.endswith('_pytimer.json')]
    if not timer_files:
        _("No exising timers found. Creating a new one.")
        return Timer(None)
    titles = []
    for timer_file in timer_files:
        fname = os.path.join(get_logdir(), timer_file)
        with open(fname, 'r') as fid:
            line = fid.readline()
            data = json.loads(line)
            titles.append(data['title'])
    for i, title, filename in zip(range(len(titles)), titles, timer_files):
        _("%i: %s\t[%s]" % (i, title, filename))
    while True:
        inp = input("Please choose a timer from the list above using "
                "the number in front of the line. ")
        if not inp.isdigit():
            _("Not a valid choice, please try again.")
            continue
        idx = int(inp)
        break
    fname = os.path.join(get_logdir(), timer_files[idx])
    return Timer.load_json(fname)

def ask_launch_new():
    while True:
        inp = input("Launch new Timer? [Y/n/q/h] ")
        inp = inp.strip()
        if (not inp) or inp.lower() == 'y':
            return True
        elif inp.lower() == 'n':
            return False
        elif inp.lower() == 'q':
            raise SystemExit
        elif inp.lower() == 'h':
            _("Options:\n\ty\tLaunch new Timer\n\tn\tLoad existing Timer\n\t"
                    "q\tQuit PyTimer\n\th\tShow this help\n")
        else:
            _("Invalid input, please try again. Type 'h' for help.")

def run_timer(timer):
    # Start the timer
    try:
        timer.run()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        timer.stop()
        print()

def parse_options():
    parser = argparse.ArgumentParser(
            description="A timing application for Python")
    parser.add_argument('-n', action='store_true', help="Start a new timer")
    parser.add_argument('-l', action='store_true',
            help="Load an existing timer")
    args = parser.parse_args()
    return args

def main():
    signal.signal(signal.SIGTERM, sigterm_hdl)
    args = parse_options()
    make_new = False
    if not (args.n or args.l):
        make_new = ask_launch_new()
    if args.n or make_new:
        timer = Timer(None)
    elif args.l or not make_new:
        timer = choose_timer()
    else:
        _("Don't know what you want. Exiting.")
        raise SystemExit
    run_timer(timer)

def sigterm_hdl(signal, frame):
    raise SystemExit

if __name__ == '__main__':
    main()
