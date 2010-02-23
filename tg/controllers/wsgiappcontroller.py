# -*- coding: utf-8 -*-
"""
"""
import pylons
from tgcontroller import TGController
from util import redirect
from tg.decorators import expose

class WSGIAppController(TGController):
    """
    A controller you can use to mount a WSGI app.
    """
    def __init__(self, app, allow_only=None):
        self.app = app
        self.allow_only = allow_only
        # Signal tg.configuration.maybe_make_body_seekable which is wrapping
        # The stack to make the body seekable so default() can rewind it.
        pylons.configuration.config['make_body_seekable'] = True
        # Calling the parent's contructor, to enable controller-wide auth:
        super(WSGIAppController, self).__init__()

    @expose()
    def _default(self, *args, **kw):
        """
        This method is called whenever a request reaches this controller.
        It prepares the WSGI environment and delegates the request to the
        WSGI app.
        """
        # Push into SCRIPT_NAME the path components that have been consumed,
        request = pylons.request._current_obj()
        new_req = request.copy()
        to_pop = len(new_req.path_info.strip('/').split('/')) - len(args)
        for i in xrange(to_pop):
            new_req.path_info_pop()
        if not new_req.path_info:
            # Append trailing slash and redirect
            redirect(request.path_info+'/')
        new_req.body_file.seek(0)
        return self.delegate(new_req.environ, request.start_response)

    def delegate(self, environ, start_response):
        """
        Delegates the request to the WSGI app.

        Override me if you need to update the environ, mangle response, etc...
        """
        return self.app(environ, start_response)


__all__ = [
    "WSGIAppController",
    ]
