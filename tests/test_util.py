# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import tg
from tg.util import *
from tg.configuration.utils import get_partial_dict
from nose.tools import eq_, raises
import os
from tg.controllers.util import *
from tg.util.dates import get_fixed_timezone, utctz, parse_datetime
from tg.util.files import safe_filename
from tg.util.html import script_json_encode
from tg.util.webtest import test_context
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


class TestUrlMethod(object):
    def test_url_unicode(self):
        with test_context(None, '/'):
            res = url('.', {'p1':u_('v1')})
            assert res == '.?p1=v1'

    def test_url_unicode_nonascii(self):
        with test_context(None, '/'):
            res = url('.', {'p1':u_('àèìòù')})
            assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

    def test_url_nonstring(self):
        with test_context(None, '/'):
            res = url('.', {'p1':1})
            assert res == '.?p1=1'

    def test_url_object(self):
        class Object(object):
            def __str__(self):
                return 'aeiou'

        with test_context(None, '/'):
            res = url('.', {'p1': Object()})
            assert res == '.?p1=aeiou'

    def test_url_object_unicodeerror(self):
        class Object(object):
            def __str__(self):
                return u_('àèìòù')

        with test_context(None, '/'):
            res = url('.', {'p1': Object()})
            assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

    def test_url_object_exception(self):
        class SubException(Exception):
            def __str__(self):
                return u_('àèìòù')

        with test_context(None, '/'):
            res = url('.', {'p1': SubException('a', 'b', 'c')})
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



class TestDatesUtils(object):
    def test_get_fixed_timezone_seconds(self):
        delta = get_fixed_timezone(0.5).utcoffset(None)
        assert delta.seconds == 0

    def test_get_fixed_timezone_minutes(self):
        delta = get_fixed_timezone(1).utcoffset(None)
        assert delta.seconds == 60

    def test_get_fixed_timezone_hours(self):
        delta = get_fixed_timezone(60).utcoffset(None)
        assert delta.seconds == 3600

    def test_get_fixed_timezone_seconds_td(self):
        delta = get_fixed_timezone(timedelta(seconds=30)).utcoffset(None)
        assert delta.seconds == 0

    def test_get_fixed_timezone_minutes_td(self):
        delta = get_fixed_timezone(timedelta(minutes=1)).utcoffset(None)
        assert delta.seconds == 60

    def test_get_fixed_timezone_hours_td(self):
        delta = get_fixed_timezone(timedelta(hours=1)).utcoffset(None)
        assert delta.seconds == 3600

    def test_get_fixed_timezone_usage(self):
        utcnow = datetime.utcnow()

        uktz = get_fixed_timezone(60)
        uknow = (utcnow + timedelta(hours=1)).replace(tzinfo=uktz)

        naiveuk = uknow.astimezone(utctz).replace(tzinfo=None)
        assert utcnow == naiveuk, (utcnow, naiveuk)

    def test_get_fixed_timezone_name(self):
        uktz = get_fixed_timezone(60)
        uktz_name = uktz.tzname(None)
        assert uktz_name == '+0100', uktz_name
        assert repr(uktz) == '<+0100>', repr(uktz)

        assert utctz.tzname(None) == 'UTC', utctz.tzname(None)
        assert repr(utctz) == '<UTC>', repr(utctz)

    def test_get_fixed_timezone_unknowndst(self):
        uktz = get_fixed_timezone(60)
        assert uktz.dst(None).seconds == 0

    def test_parse_datetime_tz(self):
        dt = parse_datetime('1997-07-16T19:20:30.45+01:00')
        assert dt.tzname() == '+0100', dt

        expected_dt = datetime(1997, 7, 16, 19, 20, 30, 450000)
        naive_dt = dt.replace(tzinfo=None)
        assert naive_dt == expected_dt, naive_dt

    def test_parse_datetime_utc(self):
        dt = parse_datetime('1997-07-16T19:20:30.45Z')
        assert dt.tzname() == 'UTC', dt

        expected_dt = datetime(1997, 7, 16, 19, 20, 30, 450000).replace(tzinfo=utctz)
        assert dt == expected_dt, dt

    def test_parse_datetime_negativetz(self):
        dt = parse_datetime('1997-07-16T19:20:30.45-01:00')
        assert dt.tzname() == '-0100', dt

        expected_dt = datetime(1997, 7, 16, 19, 20, 30, 450000)
        naive_dt = dt.replace(tzinfo=None)
        assert naive_dt == expected_dt, naive_dt

    @raises(ValueError)
    def test_parse_datetime_invalid_format(self):
        parse_datetime('1997@07@16T19:20:30.45+01:00')


class TestHtmlUtils(object):
    def test_script_json_encode(self):
        rv = script_json_encode('</script>')
        assert rv == u_('"\\u003c/script\\u003e"')
        rv = script_json_encode("<\0/script>")
        assert rv == '"\\u003c\\u0000/script\\u003e"'
        rv = script_json_encode("<!--<script>")
        assert rv == '"\\u003c!--\\u003cscript\\u003e"'
        rv = script_json_encode("&")
        assert rv == '"\\u0026"'
        rv = script_json_encode("\'")
        assert rv == '"\\u0027"'
        rv = "<a ng-data='%s'></a>" % script_json_encode({'x': ["foo", "bar", "baz'"]})
        assert rv == '<a ng-data=\'{"x": ["foo", "bar", "baz\\u0027"]}\'></a>'


class TestFilesUtils(object):
    def test_safe_filename(self):
        assert safe_filename('My cool movie.mov') == 'My_cool_movie.mov'
        assert safe_filename('../../../etc/passwd') == 'etc_passwd'
        assert safe_filename(u_('i contain cool ümläuts.txt')) == 'i_contain_cool_umlauts.txt'


class TestWebTestUtilities(object):
    def test_test_context(self):
        with test_context(None):
            test_url = url('/test')
            assert test_url == '/test', test_url

        try:
            url('/test')
        except:
            pass
        else:
            assert False, 'Should have raised exception...'

    def test_test_context_broken_app(self):
        from webtest import TestApp
        from tg import AppConfig, config
        from tg.request_local import context

        app = TestApp(AppConfig(
            minimal=True,
            root_controller=None
        ).make_wsgi_app())

        try:
            with test_context(app):
                raise RuntimeError('This is an error')
        except RuntimeError:
            pass
        else:
            assert False, 'Should have raised RuntimeError...'

        with test_context(app):
            config._pop_object()
        # Check that context got cleaned up even though config caused an exception
        assert not context._object_stack()

        with test_context(app):
            context._pop_object()
        # Check that config got cleaned up even though context caused an exception
        assert not config._object_stack()