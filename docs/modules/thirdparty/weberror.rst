:mod:`weberror` -- Weberror
===========================

.. automodule:: weberror

:mod:`weberror.errormiddleware`
-------------------------------
.. currentmodule:: weberror.errormiddleware
.. automodule:: weberror.errormiddleware
.. autoclass:: ErrorMiddleware
    :members:

:mod:`weberror.evalcontext`
---------------------------
.. currentmodule:: weberror.evalcontext
.. automodule:: weberror.evalcontext

.. autoclass:: weberror.evalcontext.EvalContext
    :members:

:mod:`weberror.evalexception`
-----------------------------
.. currentmodule:: weberror.evalexception
.. automodule:: weberror.evalexception

.. autoclass:: weberror.evalexception.EvalException
    :members:

:mod:`weberror.formatter`
-------------------------
.. currentmodule:: weberror.formatter
.. automodule:: weberror.formatter
.. autoclass:: AbstractFormatter
    :members:
.. autoclass:: TextFormatter
    :members:
.. autoclass:: HTMLFormatter
    :members:
.. autoclass:: XMLFormatter
    :members:
.. autofunction:: create_text_node
.. autofunction:: html_quote
.. autofunction:: format_html
.. autofunction:: format_text
.. autofunction:: format_xml
.. autofunction:: str2html
.. autofunction:: _str2html
.. autofunction:: truncate
.. autofunction:: make_wrappable
.. autofunction:: make_pre_wrappable


:mod:`weberror.reporter`
------------------------
.. currentmodule:: weberror.reporter
.. automodule:: weberror.reporter
.. autoclass:: Reporter
    :members:
.. autoclass:: EmailReporter
    :members:
.. autoclass:: LogReporter
    :members:
.. autoclass:: FileReporter
    :members:
.. autoclass:: WSGIAppReporter
    :members:



:mod:`weberror.collector`
-------------------------
.. currentmodule:: weberror.collector
.. automodule:: weberror.collector

.. autoclass:: ExceptionCollector
    :members:

.. autoclass:: ExceptionFrame
    :members:

.. autofunction:: collect_exception

