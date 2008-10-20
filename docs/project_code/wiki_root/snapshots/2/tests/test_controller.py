# -*- coding: utf-8 -*-
from paste.fixture import TestApp

import os.path
config = 'config:'+(os.path.abspath(os.path.basename(__name__)+'/../../development.ini#main'))

app = TestApp(config)

class TestTGController:
    def test_index(self):
        resp = app.get('/')
        assert 'TurboGears 2 is a open source front-to-back web development' in resp.body, resp.body
