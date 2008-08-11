:mod:`tg.controllers` -- Controllers
========================================

.. automodule:: tg.controllers

Core Contents
---------------

In general, the TG2 users should setup their Root object as a TGController.   That plus the redirect function, and the special url function for constructing URL's constitutes the main functionality of the Controllers.   The ObjectDispatchController, and DecoratedController provide controllers that can be used as endpoints for users who are using Routes -- either in addition to object dispatch, or as an alternative.

.. autoclass:: TGController

.. autofunction:: redirect

.. autofunction:: url

Other Classes
++++++++++++++++

.. autoclass:: DecoratedController

.. autoclass:: ObjectDispatchController

