import os
from unittest import TestCase

from paste.deploy import loadapp
import paste.fixture
from simplejson import loads

from routes import url_for

tests_dir = os.path.dirname(os.path.abspath(__file__))

class BaseTestController(TestCase):
    def __init__(self, *args):
        wsgiapp = loadapp('config:blogtutorial.ini', relative_to=tests_dir)
        self.app = paste.fixture.TestApp(wsgiapp)
        TestCase.__init__(self, *args)


class TestOutputFormat(BaseTestController):
    """Test that controller methods negotiate content type based on "expose"d
    configuration and request type."""
    def test_html(self):
        response = self.app.get(url_for('/test_json'))
        self.failUnless('Welcome to PyGears' in response)

    def test_json(self):
        #XXX This test fails.
        response = self.app.get(url_for('/test_json.json'))
        print str(response)
        json = loads(response.body)
        self.failUnlessEqual(json, dict(a=1, b=2, c={'result':'wo-hoo!'}))

class TestObjectDispatch(BaseTestController):
    """Test that object dispatch works properly"""
    
    def test_root(self):
        response = self.app.get(url_for('/'))
        self.failUnless('Welcome to PyGears' in response)

    def test_sub(self):
        response = self.app.get(url_for('/sub'))
        self.failUnless('SubIndex' in response)

class TestArgsMarshalling(BaseTestController):
    """Test that controller methods receive their positional and kw args
    properly."""

    def test_positional(self):
        r = self.app.get(url_for('/test_args/foo/bar'))
        self.failUnlessEqual(r.args, ('foo', 'bar'))

    def test_kw(self):
        r = self.app.get(url_for('/test_args?foo=1&bar=2'))
        self.failUnlessEqual(r.kw, dict(foo='1', bar='2'))

    def test_both(self):
        r = self.app.get(url_for('/test_args/foo/bar?foo=1&bar=2'))
        self.failUnlessEqual(r.kw, dict(foo='1', bar='2'))
        self.failUnlessEqual(r.args, ('foo', 'bar'))
