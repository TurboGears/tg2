"""Main Controller"""

from tg import expose, redirect, config
from tg.controllers import TGController

class RootController(TGController):
    @expose('genshi:index.html')
    def index(self):
        return {}
    
    @expose('mako:mako_noop.mak')
    def mako_index(self):
        return {}

    @expose('mako:mako_inherits.mak')
    def mako_inherits(self):
        return {}
