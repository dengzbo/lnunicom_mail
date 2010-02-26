# CENO-ADF rotatelogs script
#
#  Author: Hover
# Version: 1.0
#

import sys, signal, os, string

# Check python version
version = string.split(string.split(sys.version)[0], '.')
if map(int, version[:2]) < [2, 4]:
    message = 'This script require Python "2.4" or above, current version is ' + sys.version
    sys.stderr.write(message + os.linesep)
    sys.exit(1)

from subprocess import Popen, PIPE
from threading import Thread, Lock
from os import path, makedirs
from time import localtime, strftime, sleep

def get_filename(pattern):
    return strftime(pattern, localtime())

def make_parent_dir(filename):
    fullname = path.realpath(filename)
    parent_dir = path.dirname(fullname)
    if not path.isdir(parent_dir):
        # if the directory is already made by another process, makedirs() will raise error
        try:
            makedirs(parent_dir)
        except:
            pass

def close(stream):
    if stream is not None:
        try:
            stream.close()
        except:
            pass

class RotateLogger(Thread):
    def __init__(self, infile, outfile):
        Thread.__init__(self)
        self.infile = infile
        self.outfile = outfile
        self.lock = Lock()
        self.is_done = False
    def run(self):
        try:
            while True:
                line = self.infile.readline()
                if not line:
                    break
                try:
                    self.lock.acquire()
                    self.outfile.write(line)
                    self.outfile.flush()
                finally:
                    self.lock.release()
            self.is_done = True
        except:
            print 'Unexpected error:', sys.exc_info()[0]
            raise

def handle_active_mode(pidfile, pattern, cmd):
    make_parent_dir(pidfile)
    filename = get_filename(pattern)
    make_parent_dir(filename)

    fp = None
    
    try:
        signal.signal(1, signal.SIG_IGN)    # signal(SIGHUP, SIG_IGN)
        
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        pid = p.pid
        
        fpid = open(pidfile, 'w')
        fpid.write(str(pid))
        fpid.flush()
        fpid.close()
        
        fp = open(filename, 'a')
        fp.write('#' * 78 + os.linesep)
        fp.write('STARTED AT %s' % strftime('%Y-%m-%d %H:%M:%S', localtime()) + os.linesep)
        fp.write('#' * 78 + os.linesep)
        fp.flush()
        
        tout = RotateLogger(p.stdout, fp)
        terr = RotateLogger(p.stderr, fp)
        
        tout.start()
        terr.start()
        
        while True:
            sleep(1)
            
            if tout.is_done and terr.is_done:
                break
            
            new_filename = get_filename(pattern)
            if filename != new_filename:
                filename= new_filename
                make_parent_dir(filename)
                try:
                    tout.lock.acquire()
                    terr.lock.acquire()
                    fp.close()
                    fp = open(filename, 'a')
                    tout.outfile = terr.outfile = fp
                finally:
                    terr.lock.release()
                    tout.lock.release()
    finally:
        close(fp)

def handle_passive_mode(pattern):
    filename = get_filename(pattern)
    make_parent_dir(filename)
    
    fp = None
    try:
        signal.signal(1, signal.SIG_IGN)    # signal(SIGHUP, SIG_IGN)
        
        fp = open(filename, 'a')
        fp.write('#' * 78 + os.linesep)
        fp.write('STARTED AT %s' % strftime('%Y-%m-%d %H:%M:%S', localtime()) + os.linesep)
        fp.write('#' * 78 + os.linesep)
        fp.flush()

        while True:
            line = sys.stdin.readline()
            if not line:
                break
            new_filename = get_filename(pattern)
            if new_filename != filename:
                fp.close()
                filename = new_filename
                make_parent_dir(filename)
                fp = open(filename, 'a')
            fp.write(line)
            fp.flush()
    finally:
        close(fp)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        handle_passive_mode(sys.argv[1])
    else:
        pidfile = sys.argv[1]
        pattern = sys.argv[2]
        cmd = sys.argv[3:]
        handle_active_mode(pidfile, pattern, cmd)
