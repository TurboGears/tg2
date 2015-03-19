"""
This is a striped down version of the Python Paste Registry Module
it is not meant to be used by itself, it's only purpose is to provide
global objects for TurboGears2.

# Original Module (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""

from tg.support.objectproxy import TurboGearsObjectProxy
from tg.support import NoDefault
import itertools, time
import threading as threadinglocal

__all__ = ['StackedObjectProxy', 'RegistryManager']


def _getboolattr(obj, attrname):
    try:
        return object.__getattribute__(obj, attrname)
    except AttributeError:  # pragma: no cover
        # This is here for compatibility with other middlewares that use
        # environ['paste.registry'] to register global objects.
        return None


class StackedObjectProxy(TurboGearsObjectProxy):
    """Track an object instance internally using a stack

    The StackedObjectProxy proxies access to an object internally using a
    stacked thread-local. This makes it safe for complex WSGI environments
    where access to the object may be desired in multiple places without
    having to pass the actual object around.

    New objects are added to the top of the stack with _push_object while
    objects can be removed with _pop_object.

    """
    def __init__(self, default=NoDefault, name="Default"):
        """Create a new StackedObjectProxy

        If a default is given, its used in every thread if no other object
        has been pushed on.

        """
        self.__dict__['____name__'] = name
        self.__dict__['____local__'] = threadinglocal.local()
        if default is not NoDefault:
            self.__dict__['____default_object__'] = default

    def _current_obj(self):
        """Returns the current active object being proxied to

        In the event that no object was pushed, the default object if
        provided will be used. Otherwise, a TypeError will be raised.

        """
        try:
            objects = self.____local__.objects
        except AttributeError:
            objects = None
        if objects:
            return objects[-1][0]
        else:
            obj = self.__dict__.get('____default_object__', NoDefault)
            if obj is not NoDefault:
                return obj
            else:
                raise TypeError(
                    'No object (name: %s) has been registered for this '
                    'thread' % self.____name__)

    def _push_object(self, obj):
        """Make ``obj`` the active object for this thread-local.

        This should be used like:

        .. code-block:: python

            obj = yourobject()
            module.glob = StackedObjectProxy()
            module.glob._push_object(obj)
            try:
                ... do stuff ...
            finally:
                module.glob._pop_object(conf)

        """
        try:
            self.____local__.objects.append((obj, False))
        except AttributeError:
            self.____local__.objects = []
            self.____local__.objects.append((obj, False))

    def _pop_object(self, obj=None):
        """Remove a thread-local object.

        If ``obj`` is given, it is checked against the popped object and an
        error is emitted if they don't match.

        """
        try:
            popped = self.____local__.objects.pop()
            popped_obj = popped[0]

            if obj and popped_obj is not obj:
                raise AssertionError(
                    'The object popped (%s) is not the same as the object '
                    'expected (%s)' % (popped_obj, obj))
        except (AttributeError, IndexError):
            raise AssertionError('No object has been registered for this thread')

    def _object_stack(self):
        """Returns all of the objects stacked in this container

        (Might return [] if there are none)
        """
        try:
            try:
                objs = self.____local__.objects
            except AttributeError:
                return []
            return objs[:]
        except AssertionError: #pragma: no cover
            return []

    def _preserve_object(self):
        try:
            object, preserved = self.____local__.objects[-1]
        except (AttributeError, IndexError):
            return

        self.____local__.objects[-1] = (object, True)

    @property
    def _is_preserved(self):
        try:
            objects = self.____local__.objects
        except AttributeError:
            return False

        if not objects:
            return False

        object, preserved = objects[-1]
        return preserved


class Registry(object):
    """Track objects and stacked object proxies for removal

    The Registry object is instantiated a single time for the request no
    matter how many times the RegistryManager is used in a WSGI stack. Each
    RegistryManager must call ``prepare`` before continuing the call to
    start a new context for object registering.

    Each context is tracked with a dict inside a list. The last list
    element is the currently executing context. Each context dict is keyed
    by the id of the StackedObjectProxy instance being proxied, the value
    is a tuple of the StackedObjectProxy instance and the object being
    tracked.

    """
    def __init__(self, enable_preservation=False):
        """Create a new Registry object

        ``prepare`` must still be called before this Registry object can be
        used to register objects.

        """
        self.reglist = []

        #preservation makes possible to keep around the objects
        #this is especially useful when debugging to avoid
        #discarding the objects after request completion.
        self.enable_preservation = enable_preservation

    def prepare(self):
        """Used to create a new registry context

        Anytime a new RegistryManager is called, ``prepare`` needs to be
        called on the existing Registry object. This sets up a new context
        for registering objects.

        """
        self.reglist.append({})

    def register(self, stacked, obj):
        """Register an object with a StackedObjectProxy"""

        if stacked is None:  # pragma: no cover
            # makes possible to disable registering for some
            # stacked objects by setting them to None.
            return

        myreglist = self.reglist[-1]
        stacked_id = id(stacked)
        if stacked_id in myreglist:
            stacked._pop_object(myreglist[stacked_id][1])
            del myreglist[stacked_id]

        # Avoid leaking memory on successive request when preserving objects
        if _getboolattr(stacked, '_is_preserved'):
            stacked._pop_object()

        stacked._push_object(obj)
        myreglist[stacked_id] = (stacked, obj)

    def cleanup(self):
        """Remove all objects from all StackedObjectProxy instances that
        were tracked at this Registry context"""
        for stacked, obj in self.reglist[-1].values():
            if not _getboolattr(stacked, '_is_preserved'):
                stacked._pop_object(obj)
        self.reglist.pop()

    def preserve(self, force=False):
        if not self.enable_preservation and force is False:
            return

        for stacked, obj in self.reglist[-1].values():
            if hasattr(stacked, '_preserve_object'):
                stacked._preserve_object()


class RegistryManager(object):
    """Creates and maintains a Registry context

    RegistryManager creates a new registry context for the registration of
    StackedObjectProxy instances. Multiple RegistryManager's can be in a
    WSGI stack and will manage the context so that the StackedObjectProxies
    always proxy to the proper object.

    The object being registered can be any object sub-class, list, or dict.

    Registering objects is done inside a WSGI application under the
    RegistryManager instance, using the ``environ['paste.registry']``
    object which is a Registry instance.

    """
    def __init__(self, application, streaming=False, preserve_exceptions=False):
        self.application = application
        self.streaming = streaming
        self.preserve_exceptions = preserve_exceptions

    def __call__(self, environ, start_response):
        app_iter = None
        reg = environ.setdefault('paste.registry', Registry(self.preserve_exceptions))
        reg.prepare()

        try:
            app_iter = self.application(environ, start_response)
        except:
            reg.preserve()
            reg.cleanup()
            raise
        else:
            # If we are streaming streaming_iter will cleanup things for us
            if not self.streaming:
                reg.cleanup()

        if self.streaming:
            return self.streaming_iter(reg, app_iter)

        return app_iter

    def streaming_iter(self, reg, data):
        try:
            for chunk in data:
                yield chunk
        except:
            reg.preserve()
            raise
        finally:
            if hasattr(data, 'close'):
                data.close()
            reg.cleanup()


class DispatchingConfig(StackedObjectProxy):
    """
    This is a configuration object that can be used globally,
    imported, have references held onto.  The configuration may differ
    by thread (or may not).

    Specific configurations are registered (and deregistered) either
    for the process or for threads.
    """
    # @@: What should happen when someone tries to add this
    # configuration to itself?  Probably the conf should become
    # resolved, and get rid of this delegation wrapper

    def __init__(self, name='DispatchingConfig'):
        super(DispatchingConfig, self).__init__(name=name)
        self.__dict__['_process_configs'] = []

    def push_thread_config(self, conf):
        """
        Make ``conf`` the active configuration for this thread.
        Thread-local configuration always overrides process-wide
        configuration.

        This should be used like::

            conf = make_conf()
            dispatching_config.push_thread_config(conf)
            try:
                ... do stuff ...
            finally:
                dispatching_config.pop_thread_config(conf)
        """
        self._push_object(conf)

    def pop_thread_config(self, conf=None):
        """
        Remove a thread-local configuration.  If ``conf`` is given,
        it is checked against the popped configuration and an error
        is emitted if they don't match.
        """
        self._pop_object(conf)

    def push_process_config(self, conf):
        """
        Like push_thread_config, but applies the configuration to
        the entire process.
        """
        self._process_configs.append(conf)

    def pop_process_config(self, conf=None):
        self._pop_from(self._process_configs, conf)

    def _pop_from(self, lst, conf):
        popped = lst.pop()
        if conf is not None and popped is not conf:
            raise AssertionError(
                "The config popped (%s) is not the same as the config "
                "expected (%s)"
                % (popped, conf))

    def _current_obj(self):
        try:
            return super(DispatchingConfig, self)._current_obj()
        except TypeError:
            if self._process_configs:
                return self._process_configs[-1]
            raise AttributeError(
                "No configuration has been registered for this process "
                "or thread")
    current = current_conf = _current_obj
