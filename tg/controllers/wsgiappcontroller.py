# -*- coding: utf-8 -*-
"""This module contains the main WSGI controller implementation."""
import tg

from tg.decorators import expose

from tg.controllers.tgcontroller import TGController
from tg.controllers.util import redirect


class WSGIAppController(TGController):
    """
    A controller you can use to mount a WSGI app.
    """
    def __init__(self, app, allow_only=None):
        self.app = app
        self.allow_only = allow_only

        # Calling the parent's contructor, to enable controller-wide auth:
        super(WSGIAppController, self).__init__()

    @expose()
    def _default(self, *args, **kw):
        """The default controller method.

        This method is called whenever a request reaches this controller.
        It prepares the WSGI environment and delegates the request to the
        WSGI app.

        """
        body_is_seekable = tg.config.get('make_body_seekable', False)
        if not body_is_seekable:
            raise RuntimeError('Mounting nested WSGI apps requires make_body_seekable=True option')

        # Push into SCRIPT_NAME the path components that have been consumed,
        request = tg.request._current_obj()
        new_req = request.copy()
        to_pop = len(new_req.path_info.strip('/').split('/')) - len(args)
        for i in range(to_pop):
            new_req.path_info_pop()

        if not new_req.path_info: #pragma: no cover
            # This should not happen
            redirect(request.path_info + '/')

        new_req.body_file.seek(0)
        return self.delegate(new_req)

    def delegate(self, request):
        """Delegate the request to the WSGI app.

        Override me if you need to update the environ, mangle response, etc...

        """
        return request.get_response(self.app)


__all__ = ['WSGIAppController']
