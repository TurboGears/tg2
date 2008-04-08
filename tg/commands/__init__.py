"""
TurboGears command line tools.

TurboGears commands are the extensions based on 'paster' command.

You could investigating all paster commands with following command::

    $ paster --help

All TurboGears commands are grouped in the 'TurboGears2' section.

Or you could check out the TurboGears-related infomation with command::

    $ paster tginfo

To create a new project named helloworld, you could start with quickstart command::

    $ paster quickstart helloworld

Then, you could run the created project with these commands::

    $ cd helloworld
    $ paster serve --reload development.ini

The command loads our project server configuration file in development.ini and
serves the TurboGears 2 application.

The --reload option ensures that the server is automatically reloaded if you
make any changes to Python files or the development.ini config file.
This is very useful during development.

To stop the server, you can press Ctrl+c or your platform's equivalent.

If you visit http://127.0.0.1:8080/ when the server is running, you will see the
welcome page (127.0.0.1 is a special IP address that references your own computer,
but you can change the hostname by editing the development.ini file).
"""
