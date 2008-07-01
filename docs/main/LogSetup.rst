Configuring and using the Logging System
=========================================

:Status: Unofficial

The `Pylons logging wiki`_ has a well written and clearly documented logging HOWTO which this document will refer to. Each of the sections documented there have been tested under TG2 and they all are functional.

The logging system can be setup through the application ini file using the `standard python logging`_ configuration layout.

To enable logging in your code, you will need to include the following::

    import logging
    log = logging.getLogger(__name__)

To prefix the logged message with your module name, use the special python variable *__name__*. Or, substitute *__name__* for anything that makes sense to you.

Call the appropriate log level method on the Logger object to send a message to the log handler::

    log.debug("This is a code debug")

By default, the root logger is set to INFO and will log to STDERR on the console.

To enable the viewing of ALL messages within the pylons and TG stacks you will need to add the following to your ini files::

    [loggers]
    keys = root
    
    [logger_root]
    level = NOTSET
    handlers = console
    
    [handlers]
    keys = console
    
    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = generic
    
    [formatters]
    keys = generic
    
    [formatter_generic]
    format = %(asctime)s,%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s
    datefmt = %H:%M:%S

    

As an additional reference to the pylons write up, the RotatingFileHandler_ class is documented here::

    [handler_accesslog]
    class = handlers.RotatingFileHandler
    args = ('access.log','a', 10000, 4)
    level = DEBUG
    formatter = accesslog

``class``
 refers to a python class in the logging_ or logging.handlers_ module.
``args``
 refers to the parameters required for the instantiation or initialization of the above class.

In this example 4 backup files are being kept and the log is rotated when the file size reaches 10000 bytes.

.. _standard python logging: http://docs.python.org/lib/logging-config-fileformat.html
.. _RotatingFileHandler: http://docs.python.org/lib/node413.html
.. _logging: http://docs.python.org/lib/module-logging.html
.. _logging.handlers: http://docs.python.org/lib/node410.html
.. _Pylons logging wiki: http://wiki.pylonshq.com/display/pylonsdocs/Logging
