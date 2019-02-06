TurboGears
==========

.. image:: https://travis-ci.org/TurboGears/tg2.png?branch=development
    :target: https://travis-ci.org/TurboGears/tg2

.. image:: https://coveralls.io/repos/TurboGears/tg2/badge.png?branch=development
    :target: https://coveralls.io/r/TurboGears/tg2?branch=development

.. image:: https://img.shields.io/pypi/v/TurboGears2.svg
   :target: https://pypi.python.org/pypi/TurboGears2

.. image:: https://img.shields.io/pypi/pyversions/TurboGears2.svg
    :target: https://pypi.python.org/pypi/TurboGears2

.. image:: https://img.shields.io/pypi/l/TurboGears2.svg
    :target: https://pypi.python.org/pypi/TurboGears2

.. image:: https://www.codetriage.com/turbogears/tg2/badges/users.svg
    :target: https://www.codetriage.com/turbogears/tg2

.. image:: https://img.shields.io/gitter/room/turbogears/Lobby.svg
    :target: https://gitter.im/turbogears/Lobby

.. image:: https://img.shields.io/twitter/follow/turbogearsorg.svg?style=social&label=Follow
    :target: https://twitter.com/turbogearsorg

TurboGears is a hybrid web framework able to act both as a Full Stack
framework or as a Microframework. TurboGears helps you get going fast
and gets out of your way when you want it!


TurboGears can be used *both* as a *full stack* framework or as a
*microframework* in single file mode.

Get Started
-----------

**NOTE: This is development branch**,
for current stable release refer to `Documentation <http://turbogears.readthedocs.io/>`_

.. image:: https://asciinema.org/a/181221.png
    :target: https://asciinema.org/a/181221

To try TurboGears just get ``pip`` if you don't already have it::

    $ curl -O 'https://bootstrap.pypa.io/get-pip.py'
    $ python get-pip.py

And install Turbogears::

    $ pip install --pre TurboGears2

Then serving a TurboGears web application is as simple as making a ``webapp.py``
file with your application::

    from wsgiref.simple_server import make_server
    from tg import MinimalApplicationConfigurator
    from tg import expose, TGController

    # RootController of our web app, in charge of serving content for /
    class RootController(TGController):
        @expose(content_type="text/plain")
        def index(self):
            return 'Hello World'

    # Configure a new minimal application with our root controller.
    config = MinimalApplicationConfigurator()
    config.update_blueprint({
        'root_controller': RootController()
    })

    # Serve the newly configured web application.
    print("Serving on port 8080...")
    httpd = make_server('', 8080, config.make_wsgi_app())
    httpd.serve_forever()


Start it with ``python webapp.py`` and open your browser at ``http://localhost:8080/``

Want to play further with TurboGears? Try the TurboGears Tutorials:

* `Getting Started with Turbogears <http://turbogears.readthedocs.io/en/latest/turbogears/minimal/index.html>`_
* `Building a Wiki in 20 minutes <http://turbogears.readthedocs.io/en/latest/turbogears/wiki20.html>`_

Support and Documentation
-------------------------

Visit `TurboGears Documentation <http://turbogears.readthedocs.io/>`_ for
complete **documentation** and **tutorials**.

See the `TurboGears website <http://www.turbogears.org/>`_ to get
a quick overview of the framework and look for support.

License
-------

TurboGears is licensed under an MIT-style license (see LICENSE.txt).
Other incorporated projects may be licensed under different licenses.
All licenses allow for non-commercial and commercial use.


