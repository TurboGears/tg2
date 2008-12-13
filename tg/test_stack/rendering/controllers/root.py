"""Main Controller"""

from tg import expose, redirect, config
from tg.controllers import TGController

class RootController(TGController):
    @expose('genshi:tg.test_stack.rendering.templates.index')
    def index(self):
        return {}
    
    @expose('mako:tg.test_stack.rendering.templates.mako_noop')
    def mako_index(self):
        return {}

    @expose('mako:tg.test_stack.rendering.templates.mako_inherits')
    def mako_inherits(self):
        return {}
