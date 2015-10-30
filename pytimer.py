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

 +==============================+
 | Title:            Test Timer |
 | Status:              RUNNING |
 |                              |
 |           History            |
 | Date                Total    |
 | ----------          -------- |
 | 2015-05-03          00:10:00 |
 | 2015-05-04          00:15:00 |
 | Total 	       00:25:00 |
 |                              |
 |            Today             |
 | Changed at          Elapsed  |
 | ----------          -------- |
 | 23:51:06            00:00:00 | <- green
 | 23:55:16            00:04:10 | <- red
 | 23:55:20            00:04:10 | <- green
 |                              |
 | Total Elapsed:      00:25:01 |
 | Current Time:       23:33:08 |
 +==============================+

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

def sec2str(seconds):
    hours = seconds // 3600
    minutes = (seconds - 3600*hours) // 60
    secs = (seconds % 60) // 1
    return '%02i:%02i:%02i' % (hours, minutes, secs)

class LoopPrinter(object):

    LEDGE = colored(' | ', 'yellow')
    REDGE = colored(' |\n', 'yellow')

    def __init__(self):
        self.text = []
        self.running = False
        self.die = False

    def run(self):
        self.running = True

    def launch(self):
        while not self.die:
            if self.running:
                self.remove_last()
                self.add_time()
                self.print_out()
            time.sleep(1)

    def stop(self):
        self.die = True

    def add_time(self):
        dt = datetime.datetime.now()
        msg = ('Current Time:', dt.strftime('%H:%M:%S'))
        self.add_line(msg, align='border')

    def add_line(self, line, align='left', color='white'):
        self.text.append((align, line, color))

    def make_boxed(self):
        maxlen = 0
        for align, line, color in self.text:
            if isinstance(line, list) or isinstance(line, tuple):
                maxlen = max([maxlen, 6+sum([len(x) for x in line])])
            else:
                maxlen = max([maxlen, len(line)])
        s = ''
        topbottom = colored(' +' + '='*(maxlen+2) + '+', 'yellow')
        s += topbottom + '\n'
        for align, line, color in self.text:
            if align == 'left':
                l = maxlen - len(line)
                s += self.LEDGE + colored(line, color) + ' '*l + self.REDGE
            elif align == 'right':
                l = maxlen - len(line)
                s += self.LEDGE + ' '*l + colored(line, color) + self.REDGE
            elif align == 'center':
                if maxlen % 2 == 0:
                    l1 = int((maxlen - len(line))/2)
                    l2 = l1 + 1
                else:
                    l1 = int((maxlen - len(line))/2)
                    l2 = int((maxlen - len(line))/2)
                s += (self.LEDGE + ' '*l1 + colored(line, color) + ' '*l2 + 
                        self.REDGE)
            elif align == 'border' and len(line) == 2:
                lenspaces = maxlen - len(line[0]) - len(line[1])
                lenspaces = max(lenspaces, 1)
                s += (self.LEDGE + colored(line[0], color) + ' '*lenspaces + 
                        colored(line[1], color) + self.REDGE)
        s += topbottom
        return s

    def remove_last(self):
        if len(self.text):
            tmp = self.text.pop()

    def clear(self):
        del self.text
        self.text = []

    def print_out(self):
        boxed = self.make_boxed()
        os.system('cls' if os.name == 'nt' else 'clear')
        for line in boxed.split('\n'):
            sys.stdout.write(line + '\r\n')
        sys.stdout.flush()

class TimerHistory(object):

    def __init__(self, json_file=None):
        self.history = {}
        if not json_file is None:
            self.read_json_file(json_file)

    def add_record(self, record):
        # record is (date_obj, seconds)
        date, seconds = record
        if date in self.history:
            self.history[date] += seconds
        else:
            self.history[date] = seconds

    def read_json_file(self, filename):
        with open(filename, 'r') as fid:
            lines = fid.readlines()
        for line in lines:
            self.read_json_line(line)

    def read_json_line(self, jsonline):
        data = json.loads(jsonline)
        start_t = dateutil.parser.parse(data['start_time'])
        end_t = dateutil.parser.parse(data['end_time'])
        seconds = (end_t - start_t).total_seconds()
        date = start_t.date()
        record = (date, seconds)
        self.add_record(record)

    def get_total(self):
        total = 0
        for date in self.history:
            total += self.history[date]
        return total

    def make_table_lines(self):
        if not self.history:
            return []
        lines = []
        lines.append((('Date', 'Elapsed '), 'border', 'yellow'))
        lines.append((('-'*10, '-'*8), 'border', 'yellow'))
        for date in sorted(self.history):
            datestr = date.strftime('%Y-%m-%d')
            secstr = sec2str(self.history[date])
            lines.append(((datestr, secstr), 'border', 'white'))
        total = self.get_total()
        lines.append((('Total', sec2str(total)), 'border', 'magenta'))
        return lines

class Logger(object):

    def __init__(self, title):
        self.title = title
        self.log_file = self.get_logfile()
        self.json_file = self.get_jsonfile()

    def get_logfile(self):
        fname = ('%s/pytimer_%s.log' % (get_logdir(),
            self.title.lower().replace(' ', '_')))
        return fname

    def get_jsonfile(self):
        fname = ('%s/pytimer_%s.json' % (get_logdir(),
            self.title.lower().replace(' ', '_')))
        return fname

    def log_state(self, is_running, seconds):
        epoch_secs = (datetime.datetime.now() - EPOCH).total_seconds()
        with open(self.log_file, 'a') as fid:
            if is_running:
                fid.write('%i: RUNNING: %i\n' % (epoch_secs, seconds))
            else:
                fid.write('%i: HALTED: %i\n' % (epoch_secs, seconds))

    def log_json(self, start_t, end_t):
        if start_t is None or end_t is None:
            return
        data = {'start_time': start_t.strftime('%c'),
                'end_time': end_t.strftime('%c'),
                'title': self.title}
        with open(self.json_file, 'a') as fid:
            json.dump(data, fid, sort_keys=True)
            fid.write('\n')

class Timer(object):

    def __init__(self, title=None, json_file=None):
        self.is_running = False
        self.current_seconds = 0
        self.time = datetime.datetime.now()
        self.start_time = None
        self.end_time = None
        self.title = title
        self.thread = None
        self.current_lines = []

        self.init_title()
        self.timer_history = TimerHistory(json_file)
        self.logger = Logger(self.title)
        self.loop_printer = None

        self.setup()

    def init_title(self):
        if self.title is None:
            qry = input("Enter timer name: ")
            if not qry.strip():
                epoch = (datetime.datetime.now() - EPOCH).total_seconds()
                self.title = str(round(epoch))
                _("Using unnamed timer.")
            else:
                self.title = qry.strip()
                _("Using timer name: {}".format(self.title))

    def cleanup(self):
        if self.is_running:
            self.switch()
            time.sleep(1)
        self.loop_printer.stop()
        self.thread.join()

    def setup(self):
        self.loop_printer = LoopPrinter()
        self.thread = threading.Thread(target=self.loop_printer.launch)
        self.thread.start()

    def start(self):
        self.switch()
        self.loop_printer.run()
        while True:
            k = readchar.readkey()
            if k == ' ':
                self.switch()
            if k == 'q':
                raise SystemExit

    def switch(self):
        if self.is_running:
            diff = datetime.datetime.now() - self.time
            self.current_seconds += diff.total_seconds()
            self.end_time = datetime.datetime.now()
            self.logger.log_json(self.start_time, self.end_time)
        else:
            self.start_time = datetime.datetime.now()
        self.time = datetime.datetime.now()
        self.is_running = not self.is_running
        self.logger.log_state(self.is_running, self.current_seconds)
        self.save_state()
        self.make_report()

    def save_state(self):
        elaps = sec2str(self.current_seconds)
        if self.is_running:
            line = (((self.time.strftime('%H:%M:%S'), elaps), 'border', 
                'green'))
        else:
            line = (((self.time.strftime('%H:%M:%S'), elaps), 'border', 
                'red'))
        self.current_lines.append(line)

    def get_current_table(self):
        if not self.current_lines:
            return []
        lines = []
        lines.append((('Changed at', 'Elapsed '), 'border', 'yellow'))
        lines.append((('-'*10, '-'*8), 'border', 'yellow'))
        lines.extend(self.current_lines)
        return lines

    def get_total_seconds(self):
        return self.timer_history.get_total() + self.current_seconds

    def make_report(self):
        self.loop_printer.clear()
        title = ('Title:', self.title)
        self.loop_printer.add_line(title, align='border', color='blue')
        if self.is_running:
            status = ('Status:', 'RUNNING')
            self.loop_printer.add_line(status, align='border', color='green')
        else:
            status = ('Status:', 'HALTED')
            self.loop_printer.add_line(status, align='border', color='red')
        self.loop_printer.add_line('')
        history = self.timer_history.make_table_lines()
        if history:
            self.loop_printer.add_line('History', align='center', 
                    color='white')
            for line in history:
                self.loop_printer.add_line(*line)
            self.loop_printer.add_line('')
        self.loop_printer.add_line('Today', align='center', color='white')
        current = self.get_current_table()
        if current:
            for line in current:
                self.loop_printer.add_line(*line)
            self.loop_printer.add_line('')
        self.loop_printer.add_line(('Total Elapsed:',
            sec2str(self.get_total_seconds())), align='border', 
            color='magenta')
        self.loop_printer.add_line('')

def get_logdir():
    dirname = os.path.expanduser(os.path.join('~', '.' + APPNAME))
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return dirname

def choose_timer():
    files = os.listdir(get_logdir())
    timer_files = [x for x in files if x.endswith('.json')]
    if not timer_files:
        _("No exising timers found. Creating a new one.")
        return Timer(None)
    tuples = []
    for timer_file in timer_files:
        fname = os.path.join(get_logdir(), timer_file)
        with open(fname, 'r') as fid:
            lines = fid.readlines()
            data = json.loads(lines[-1])
            latest = dateutil.parser.parse(data['end_time'])
            tup = (latest, data['title'], fname)
            tuples.append(tup)
    tuples.sort(reverse=True)
    for i, tup in zip(range(len(tuples)), tuples):
        _("%i: %s" % (i, tup[1]))
    while True:
        inp = input("Please choose a timer from the list above using "
                "the number in front of the line. ")
        if inp.strip() == 'q':
            raise SystemExit
        if not inp.isdigit():
            _("Not a valid choice, please try again.")
            continue
        idx = int(inp)
        break
    dt, title, fname = tuples[idx]
    return Timer(title=title, json_file=fname)

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
        timer.start()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        timer.cleanup()
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
