#!/usr/bin/env python
import os,sys, time
import subprocess

def _help():
        "Custom help text for tg-admin2."

        print """
TurboGears: command line interface
Usage: tg-admin2 quickstart 'projectname' """

if len(sys.argv) > 2:
    if sys.argv[1] == 'quickstart':
        print "running command:"
        print 'paster create --template=turbogears2', sys.argv[2]
        time.sleep(1)
        subprocess.Popen('paster create --template=turbogears2 ' + sys.argv[2], shell=True)
    else:
        _help()
else:
    _help()
