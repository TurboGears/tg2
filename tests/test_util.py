# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from unittest import mock

import pytest

import tg
from tg.controllers.util import url
from tg.util.bunch import Bunch, get_partial_dict
from tg.util.dates import get_fixed_timezone, parse_datetime, utctz
from tg.util.files import DottedFileLocatorError, DottedFileNameFinder, safe_filename
from tg.util.html import script_json_encode
from tg.util.instance_method import im_class
from tg.util.lazystring import LazyString
from tg.util.misc import unless
from tg.util.webtest import test_context
from tg.validation import Convert, TGValidationError
from tg.wsgiapp import AttribSafeTemplateContext, TemplateContext

path = None
def setup_module():
    global path
    path = os.curdir
    os.chdir(os.path.abspath(os.path.dirname(os.path.dirname(tg.__file__))))

def teardown_module():
    global path
    os.chdir(path)

def test_get_partial_dict():
    assert get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3}) == {'xyz':1,'zyx':2}

def test_im_class():
    class FakeClass(object):
        def method(self):
            pass

    def func():
        pass

    o = FakeClass()
    assert im_class(o.method) == FakeClass
    assert im_class(func) == None


class TestUrlMethod(object):
    def test_url_unicode(self):
        with test_context(None, '/'):
            res = url('.', {'p1':str('v1')})
            assert res == '.?p1=v1'

    def test_url_unicode_nonascii(self):
        with test_context(None, '/'):
            res = url('.', {'p1':str('àèìòù')})
            assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

    def test_url_nonstring(self):
        with test_context(None, '/'):
            res = url('.', {'p1':1})
            assert res == '.?p1=1'

    def test_url_bytes(self):
        with test_context(None, '/'):
            res = url('.', {'p1': b'hi'})
            assert res == '.?p1=hi'

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
                return str('àèìòù')

        with test_context(None, '/'):
            res = url('.', {'p1': Object()})
            assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

    def test_url_object_exception(self):
        class SubException(Exception):
            def __str__(self):
                return str('àèìòù')

        with test_context(None, '/'):
            res = url('.', {'p1': SubException('a', 'b', 'c')})
            assert res == '.?p1=a+b+c', res

    def test_url_https(self):
        with test_context(None, '/index'):
            res = url('/users', qualified=True, scheme='https')
            assert res == 'https://localhost/users', res


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

    def test_del_entry_fail(self):
        d = Bunch()
        with pytest.raises(AttributeError):
            del d.not_existing


class TestDottedNameFinder(object):
    def test_non_python_package(self):
        with pytest.raises(DottedFileLocatorError):
            DottedFileNameFinder().get_dotted_filename('this.is.not.a.python.package')

    def test_local_file(self):
        abspath = os.path.abspath('this_should_be_my_template')
        assert DottedFileNameFinder().get_dotted_filename('this_should_be_my_template') == abspath

    def test_local_file_utility_method(self):
        abspath = os.path.abspath('this_should_be_my_template')
        assert DottedFileNameFinder.lookup('this_should_be_my_template') == abspath

    def test_local_file_returns_absolute_path(self):
        assert os.path.isabs(DottedFileNameFinder.lookup('this_should_be_my_template'))

    def test_load_from_zipped_egg(self):
        import sys
        eggfile = os.path.join(os.path.dirname(__file__), 'fixtures', 'fakepackage.zip')
        sys.path.append(eggfile)

        tmplf = DottedFileNameFinder().get_dotted_filename('fakepackage.test_template',
                                                           template_extension='.xhtml')
        with open(tmplf) as t:
            template = t.read()
            assert template == '<p>Your application is now running</p>', template

    def test_py38_support(self):
        importlib_resources = mock.MagicMock(spec=["path"])
        importlib_resources.path = mock.MagicMock(
            return_value=mock.MagicMock(__enter__=mock.MagicMock(return_value="THISFILE"))
        )
        with mock.patch("importlib.resources", new=importlib_resources):
            res = DottedFileNameFinder().get_dotted_filename('tg.tests_tests_py38_support')
        assert res == os.path.abspath('THISFILE')

    def test_filenotfound(self):
        exc = FileNotFoundError()
        exc.filename = "FILENAME"
        with mock.patch("importlib.resources", new=mock.MagicMock(
            as_file=mock.MagicMock(side_effect=exc)
        )):
            res = DottedFileNameFinder().get_dotted_filename('tg.tests_test_filenotfound')
        assert res == os.path.abspath("FILENAME")

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

    def test_lazy_string_with_genshi(self):
        # See https://github.com/TurboGears/tg2/pull/68
        from genshi.template.markup import MarkupTemplate
        markup = """<b xmlns:py="http://genshi.edgewall.org/">${foo}</b>"""
        template = MarkupTemplate(markup)
        stream = template.generate(foo=LazyString(lambda: "bar"))
        output = str(stream)  # Contains only ascii char, so it should cast fine on both py2 and py3
        assert output == '<b>bar</b>', output


class TestAttribSafeContextObj(object):
    def setup_method(self):
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

    def test_parse_datetime_invalid_format(self):
        with pytest.raises(ValueError):
            parse_datetime('1997@07@16T19:20:30.45+01:00')


class TestHtmlUtils(object):
    def test_script_json_encode(self):
        rv = script_json_encode('</script>')
        assert rv == str('"\\u003c/script\\u003e"')
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

    def test_script_json_encode_array(self):
        rv = "<a ng-data='%s'></a>" % script_json_encode(['1', 2, 5])
        assert rv == '<a ng-data=\'["1", 2, 5]\'></a>', rv


class TestFilesUtils(object):
    def test_safe_filename(self):
        assert safe_filename('My cool movie.mov') == 'My_cool_movie.mov'
        assert safe_filename('../../../etc/passwd') == 'etc_passwd'
        assert safe_filename(str('i contain cool ümläuts.txt')) == 'i_contain_cool_umlauts.txt'


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


class TestMiscUtils(object):
    def test_unless(self):
        not5 = unless(lambda x: x % 5, 0)
        assert not5(6) == 1

        with pytest.raises(ValueError):
            not5(10)

    def test_unless_sqla(self):
        from sqlalchemy import (
            Column,
            Integer,
            String,
            Table,
            create_engine,
        )
        from sqlalchemy.orm import Session, registry

        engine = create_engine("sqlite:///:memory:")
        mapper_registry = registry()
        metadata = mapper_registry.metadata
        testtable = Table('test1', metadata,
            Column('id', Integer, primary_key=True),
            Column('val', String(8)))
        metadata.create_all(engine)

        class Test(object):
            pass
        mapper_registry.map_imperatively(Test, testtable)

        with engine.connect() as connection:
            connection.execute(testtable.insert(), {'id': 1, 'val': 'bob'})
            connection.execute(testtable.insert(), {'id': 2, 'val': 'bobby'})
            connection.execute(testtable.insert(), {'id': 3, 'val': 'alberto'})

            sess = Session(connection)
            getunless = unless(lambda x: sess.get(Test, x))

            x = getunless(1)
            assert x.val == 'bob', x

            x = getunless(2)
            assert x.val == 'bobby', x

            with pytest.raises(ValueError):
                getunless(5)

            with pytest.raises(TGValidationError):
                Convert(getunless).to_python('5')

            x = Convert(getunless).to_python('1')
            assert x.val == 'bob', x