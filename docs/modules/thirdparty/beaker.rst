:mod:`beaker` -- Caching
========================
.. _beaker:

======
Beaker
======


Cache
-----

.. currentmodule:: beaker.cache

.. automodule:: beaker.cache

.. autoclass:: Cache
    :members:
.. autoclass:: CacheManager
    :members:


Container
---------

.. currentmodule:: beaker.container

.. automodule:: beaker.container
.. autoclass:: ContainerContext
.. autoclass:: Container
.. autoclass:: MemoryContainer
.. autoclass:: DBMContainer
.. autoclass:: NamespaceManager
.. autoclass:: MemoryNamespaceManager
.. autoclass:: DBMNamespaceManager
.. autoclass:: FileContainer
.. autoclass:: FileNamespaceManager
.. autoclass:: CreationAbortedError
.. autofunction:: container_registry
.. autofunction:: namespace_registry


Database
--------

.. currentmodule:: beaker.ext.database

.. automodule:: beaker.ext.database
.. autoclass:: DatabaseNamespaceManager
.. autoclass:: DatabaseContainer


Memcached
---------
.. currentmodule:: beaker.ext.memcached

.. automodule:: beaker.ext.memcached
.. autoclass:: MemcachedNamespaceManager
.. autoclass:: MemcachedContainer


Middleware

.. currentmodule:: beaker.middleware

.. automodule:: beaker.middleware
.. autoclass:: CacheMiddleware
.. autoclass:: SessionMiddleware

Session
-------
.. currentmodule:: beaker.session

.. automodule:: beaker.session
.. autoclass:: SignedCookie
.. autoclass:: Session
.. autoclass:: SessionObject

Synchronization
---------------
.. currentmodule:: beaker.synchronization

.. automodule:: beaker.synchronization
.. autoclass:: NameLock
.. autoclass:: Synchronizer
.. autoclass:: SyncState
.. autoclass:: SynchronizerImpl
.. autoclass:: FileSynchronizer
.. autoclass:: ConditionSynchronizer


Util
----
.. currentmodule:: beaker.util

.. automodule:: beaker.util
.. autoclass:: SyncDict
.. autoclass:: Registry
.. autoclass:: WeakValuedRegistry
.. autoclass:: ThreadLocal
.. autofunction:: b64decode
.. autofunction:: b64encode
.. autofunction:: verify_directory
.. autofunction:: encoded_path
.. autofunction:: verify_options
.. autofunction:: verify_rules
.. autofunction:: coerce_session_params
.. autofunction:: coerce_cache_params






