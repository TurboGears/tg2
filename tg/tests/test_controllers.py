# -*- coding: utf-8 -*-

import tg
from tg.controllers import *
from tg.tests import TestWSGIController, make_app, create_request
from nose.tools import eq_

def test_create_request():
    environ = { 'SCRIPT_NAME' : '/xxx' }
    request = create_request('/', environ)
    eq_('http://localhost/xxx/hello', tg.request.relative_url('hello'))

def test_url():
    create_request('/')
    eq_('hello', url('hello'))
    return
    eq_('/hello', url('/hello'))
