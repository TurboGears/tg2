"""
Testing for TG2 Configuration
"""
from nose.tools import eq_, raises
import atexit

from tg.render import render, MissingRendererError
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

@raises(MissingRendererError)
def test_render_missing_renderer():
    render({}, 'gensh')
