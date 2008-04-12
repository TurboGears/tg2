

Writing controller methods
===========================

:Status: Work in progres

.. contents:: Table of Contents
    :depth: 2


SubController
-------------

To make a sub-controller, just make your sub-controller inherit from the object class::

    from lib.base import BaseController
    from tg import redirect

    class MovieController(object):
        def index(self):
            raise redirect('list')

        def list(self):
            return 'hello'

    class RootController(BaseController):
        movie = MovieController()


Reference
----------

 * Form Handling http://wiki.pylonshq.com/display/pylonsdocs/Form+Handling
 * Caching in Templates and Controllers http://wiki.pylonshq.com/display/pylonsdocs/Caching+in+Templates+and+Controllers


