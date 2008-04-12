

:status: Unofficial

Transactional Middleware
========================

The transactional middleware is a link between the controller and the ORM. The requirements for a useful solution are:

* Sensible defaults - if an application just uses an ORM without any flush/commit/rollback code, this should "just work"
* Reasonably efficient - don't cause a lot of unnecessary database traffic
* Able to override behaviour
* Pluggable support for different ORMs; at least an SQLAlchemy module initially
* Support multiple databases
* Able to support advanced features - retry on transient errors, two phase commit, etc.

Note: transactional middleware does not cover: a command line app for managing the database; configuration to point a TG app at a database.


Design
------

The basic design is this:

* Before request - begin transaction
* After a request, is it:

 * Successful? - commit
 * Error? - rollback

The main consideration for efficiency is that transactions should only be needed on write HTTP methods - POST, PUT and DELETE. Note that for ORMs that use the unit of work pattern (such as SQLAlchemy) the efficiency issue is somewhat less important, and the "begin transaction" command is only sent database when the database is actually used.

There is a challenge around how the application can gain manual control of the WSGI middleware - this arguably breaks the idea of middleware. It's probably better to call this a `WSGI Framework Component <http://groovie.org/articles/2007/08/18/wsgi-middleware-isnt-middleware-time-for-better-language>`_.


SQLAlchemy
----------

* When creating the middleware instance, pass it a scoped_session. This picks up a session from thread ID.
* If no transaction, still needs to do a flush after the request.
* Needs to always do a clear after the request (this is less true with later SA versions which have "weak binding" sessions)
* Multiple database should "just work" - sessions can handle multiple metadatas transparently.
* Applications can override behaviour by accessing the SA session manually.
* Some code differences will be needed for SA 0.3 and 0.4.


SQLObject
---------

TBD


Advanced Features
-----------------

Two phase commit: This is helpful when updating multiple databases, aims to ensure that either all the updates are done, or none are done.

Automatic retry: You may encounter transient errors in the controller. By far the most common one of these is when the connection to the database has been lost, either because the database was restarted or due to a timeout (common on MySQL). In principle, middleware could stop a transient error and retry. However, this is technically difficult, and will cause problems if the controller has a side effect, such as sending an email. Changes in recent versions of SQLAlchemy allow automatic reconnects, making the need for this feature less pressing.
