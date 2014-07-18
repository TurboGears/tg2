# -*- coding: utf-8 -*-

import tg
from tg.util import *
from tg.configuration.utils import get_partial_dict
from nose.tools import eq_, raises
import os
from tg.controllers.util import *
from tg.wsgiapp import TemplateContext, AttribSafeTemplateContext

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

class TestBunch(object):
    def test_add_entry(self):
        d = Bunch()
        d['test.value'] = 5
        assert d.test.value == 5

    def test_del_entry(self):
        d = Bunch()
        d['test_value'] = 5
        del d.test_value
        assert not list(d.keys())

    @raises(AttributeError)
    def test_del_entry_fail(self):
        d = Bunch()
        del d.not_existing

class TestDottedNameFinder(object):
    @raises(DottedFileLocatorError)
    def test_non_python_package(self):
        DottedFileNameFinder().get_dotted_filename('this.is.not.a.python.package')

    def test_local_file(self):
        assert DottedFileNameFinder().get_dotted_filename('this_should_be_my_template') == 'this_should_be_my_template'

    def test_local_file_utility_method(self):
        assert DottedFileNameFinder.lookup('this_should_be_my_template') == 'this_should_be_my_template'

class TestLazyString(object):
    def test_lazy_string_to_str(self):
        l = LazyString(lambda: 'HI')
        assert str(l) == 'HI'

    def test_lazy_string_to_mod(self):
        l = LazyString(lambda: '%s')
        assert (l % 'HI') == 'HI'

    def test_lazy_string_format(self):
        l = LazyString(lambda: '{0}')
        lf = l.format('HI')
        assert lf == 'HI', lf

class TestAttribSafeContextObj(object):
    def setup(self):
        self.c = AttribSafeTemplateContext()

    def test_attribute_default_value(self):
        assert self.c.something == ''

        self.c.something = 'HELLO'
        assert self.c.something == 'HELLO'

        assert self.c.more == ''

def test_tmpl_context_long_entry():
    c = TemplateContext()
    c.something = '3'*300
    assert len(str(c)) < 300
