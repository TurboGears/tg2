"""Main Controller"""

from tg import expose, redirect, config
from tg.decorators import use_custom_format
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

    @expose('mako:tg.test_stack.rendering.templates.mako_inherits_dotted')
    def mako_inherits_dotted(self):
        return {}
        
    @expose('json', custom_format='json')
    @expose('mako:mako_custom_format.mak', content_type='text/xml', custom_format='xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html', custom_format='html')
    def custom_format(self, format):
        use_custom_format(self.custom_format, format)
        return dict(format=format, status="ok")
