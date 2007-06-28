"""
blogtutorial

This file loads the finished app from blogtutorial.config.middleware.

"""
import sys
import os
import os.path as path

here = path.join(*path.split(path.dirname(__file__))[:-1])
sys.path.insert(0, here)

from blogtutorial.config.middleware import make_app
