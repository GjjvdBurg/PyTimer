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

import datetime
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

    def __init__(self):
        self.is_running = False
        self.total_seconds = 0
        self.seconds = 0
        self.time = datetime.datetime.now()
        self.clock = None
        self.title = None
        self.thread = None
        self.max_hdr_length = 0
        #self.logfile = self.init_logfile()
        self.start()

    def init_logfile(self):
        fname = ('%s/pytimer_%s.log' % (self.logdir(),
            self.title.lower().replace(' ', '_')))
        try:
            with open(fname): pass
        except IOError:
            return open(fname, 'w')
        return open(fname, 'a')

    def logdir(self):
        dirname = os.path.expanduser(os.path.join('~', '.' + APPNAME))
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        return dirname

    def log_state(self, msg):
        epoch_secs = (datetime.datetime.now() - EPOCH).total_seconds()
        self.logfile.write('%i: %s' % (epoch_secs, msg))

    def start_clock(self):
        self.clock = Clock()
        self.thread = threading.Thread(target=self.clock.start)
        self.thread.start()

    def stop_clock(self):
        self.clock.stop()
        self.thread.join()

    def start(self):
        self.ask_title()
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
        else:
            self.time = datetime.datetime.now()
        self.is_running = not self.is_running
        state = self.set_state()
        #self.log_state(state)

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
        elaps = self.elapsed_string()
        elaps += ' '*(self.max_hdr_len - len(elaps))
        total = self.total_elapsed_string()
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

    def elapsed_string(self):
        hours = self.seconds // 3600
        minutes = (self.seconds - 3600*hours) // 60
        seconds = (self.seconds % 60) // 1
        return '%02i:%02i:%02i' % (hours, minutes, seconds)

    def total_elapsed_string(self):
        hours = self.total_seconds // 3600
        minutes = (self.total_seconds - 3600*hours) // 60
        seconds = (self.total_seconds % 60) // 1
        return '%02i:%02i:%02i' % (hours, minutes, seconds)


def sigterm_hdl(signal, frame):
    raise SystemExit

def main():
    signal.signal(signal.SIGTERM, sigterm_hdl)
    timer = Timer()
    try:
        timer.run()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        timer.stop()
        print()

if __name__ == '__main__':
    main()
