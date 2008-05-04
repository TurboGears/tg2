:mod:`pylons.middleware` -- WSGI Middleware
===========================================

.. automodule:: pylons.middleware

Module Contents
---------------

.. autoclass:: StatusCodeRedirect
    :members: __init__
.. autoclass:: StaticJavascripts
.. autofunction:: ErrorHandler

Legacy
^^^^^^

.. versionchanged:: 0.9.7
    These fucntions were deprecated in Pylons 0.9.7, and have been superceded
    by the :class:`StatusCodeRedirect` middleware.

.. autofunction:: ErrorDocuments
.. autofunction:: error_mapper

