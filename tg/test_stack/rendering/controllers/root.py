"""Main Controller"""

from tg import expose, redirect, config
from tg.controllers import TGController

class RootController(TGController):
    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:genshi_inherits.html')
    def genshi_inherits(self):
        return()
    
    @expose('mako:mako_noop.mak')
    def mako_index(self):
        return {}

    @expose('mako:mako_inherits.mak')
    def mako_inherits(self):
        return {}

    @expose('genshi:tg.test_stack.rendering.templates.index')
    def index_dotted(self):
        return {}

    @expose('genshi:tg.test_stack.rendering.templates.genshi_inherits')
    def genshi_inherits_dotted(self):
        return()
    
    @expose('mako:tg.test_stack.rendering.templates.mako_noop')
    def mako_index_dotted(self):
        return {}

    @expose('mako:tg.test_stack.rendering.templates.mako_inherits')
    def mako_inherits_dotted(self):
        return {}
