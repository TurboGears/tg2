from blogtutorial.lib.base import *

class HelloController(BaseController):
    def index(self, *l, **kw):
        import pdb; pdb.set_trace()
        # Return a rendered template
        #   return render_response('/some/template.html')
        # or, Return a response object
        return Response('Hello World')
