# -*- coding: utf-8 -*-

import tg
from tg.util import *
from nose.tools import eq_
import os
from tg.controllers.util import *

import tg._compat
from tg._compat import u_

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

def test_compat_im_class():
    class FakeClass(object):
        def method(self):
            pass

    def func():
        pass

    o = FakeClass()
    assert tg._compat.im_class(o.method) == FakeClass
    assert tg._compat.im_class(func) == None

def test_url_unicode():
    res = url('.', {'p1':u_('v1')})
    assert res == '.?p1=v1'

def test_url_unicode_nonascii():
    res = url('.', {'p1':u_('àèìòù')})
    assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

def test_url_nonstring():
    res = url('.', {'p1':1})
    assert res == '.?p1=1'

def test_url_object():
    class Object(object):
        def __str__(self):
            return 'aeiou'

    res = url('.', {'p1':Object()})
    assert res == '.?p1=aeiou'

def test_url_object_unicodeerror():
    class Object(object):
        def __str__(self):
            return u_('àèìòù')

    res = url('.', {'p1':Object()})
    assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

def test_url_object_exception():
    class SubException(Exception):
        def __str__(self):
            return u_('àèìòù')

    res = url('.', {'p1':SubException('a', 'b', 'c')})
    assert res == '.?p1=a+b+c', res
