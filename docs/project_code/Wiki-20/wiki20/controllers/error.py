import os.path

import paste.fileapp
from tg import request
from pylons.controllers.util import forward
from pylons.middleware import error_document_template, media_path

from wiki20.lib.base import BaseController

class ErrorController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.
    """

    def document(self):
        """Render the error document"""
        resp = request.environ.get('pylons.original_response')
        page = error_document_template % \
            dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                 code=request.params.get('code', resp.status_int),
                 message=request.params.get('message', resp.body))
        return page

    def img(self, id):
        """Serve stock images"""
        return self._serve_file(os.path.join(media_path, 'img', id))

    def style(self, id):
        """Serve stock stylesheets"""
        return self._serve_file(os.path.join(media_path, 'style', id))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        return forward(paste.fileapp.FileApp(path))
