# -*- coding: utf-8 -*-

import tg, pylons
from tg import config, redirect
from tg.controllers import RoutingController
from tg.decorators import expose, validate, paginate


class RoutingtestController(RoutingController):
    @expose()
    def static(self):
        return 'Routingtest.static'

    @expose()
    def dynamic(self, name, page=1):
        return 'Routingtest.dynamic name=[%s] page=[%s]' % (name, page)

    @expose()
    def kwargs(self, **kwargs):
        return str(kwargs)

