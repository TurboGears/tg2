

Creating the database repository
================================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

At first, you have to have some model defined in the model/ directory.

To actually create the tables in the database, run the following on the command line::

  paster setup-app development.ini

TurboGears 2 will connect to the database and create all the tables we've defined. The database is stored in  devdata.db by default. If you change your datamodel, delete this and rerun the setup-app command.


Reference:

http://wiki.pylonshq.com/display/pylonscookbook/SQLAlchemy+0.4+for+people+in+a+hurry


