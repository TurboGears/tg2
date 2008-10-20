This the TurboGears 2 Wiki-20 application.

Installation and Setup
======================

Install ``TurboGears2`` using easy_install::

    easy_install tg2

Install ``TG Devtools`` for the additional tools::

    easy_install tg.devtools

Install ``docutils`` required for this project::

    easy_install docutils

Initialize the database and populate it with initial data::

    python initializeDB.py

Start the development server::

    paster serve --reload development.ini

Point your browser to http://localhost:8080. Enjoy :-)
