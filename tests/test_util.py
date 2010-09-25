import tg
from tg.util import *
from nose.tools import eq_
import os

path = None
def setup():
    global path
    path = os.curdir
    os.chdir(os.path.abspath(os.path.dirname(os.path.dirname(tg.__file__))))

def teardown():
    global path
    os.chdir(path)

def test_get_partial_dict():
    eq_(get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3}),
        {'xyz':1,'zyx':2})

# These tests aren't reliable if the package in question has
# entry points.

def test_get_package_name():
    eq_(get_package_name(), 'tg')

def test_get_project_name():
    eq_(get_project_name(), 'TurboGears2')

def test_get_project_meta():
    eq_(get_project_meta('requires.txt'), os.path.join('TurboGears2.egg-info', 'requires.txt'))

def test_get_model():
    eq_(get_model(), None)
