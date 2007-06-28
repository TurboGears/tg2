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


class TestTGController(BaseTestController):
    def test_html(self):
        response = self.app.get(url_for('/test_json'))
        self.failUnless('Welcome to PyGears' in response)

    def test_json(self):
        #XXX This test fails.
        response = self.app.get(url_for('/test_json.json'))
        print str(response)
        json = loads(response.body)
        self.failUnlessEqual(json, dict(a=1, b=2, c={'result':'wo-hoo!'}))
