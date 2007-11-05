Some notes regarding the tests
==============================

There's a Pylons/TG2 sample app at tg/tests/blogtutorial, copied verbatim from
the app built on the pygears sprint with a hack at blogapp/__init__.py so
blogapp* imports work inside the app.

It's currently loaded from test_controllers.py

The app can still be used standalone by:

    $ paster serve tg/tests/blogtutorial.ini
