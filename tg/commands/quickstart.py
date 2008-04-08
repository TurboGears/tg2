"""Quickstart command to generate a new project.

TurboGears 2 uses Paste to create and deploy projects as well as create new
controllers and their tests.

Quickstart takes the files from turbogears.pastetemplates and processes them to
produce a new, ready-to-run project.

Create a new project named helloworld with this command::

    $ paster quickstart helloworld

You could use TurboGears2, Pylons, and WebHelper paster commands within the
project.

Usage:

.. parsed-literal::

    paster quickstart [--version][-h|--help]
            [-p *PACKAGE*][--dry-run][-t|--templates *TEMPLATES*]
            [-s|--sqlalchemy][-o|--sqlobject][-e|--elixir][-i|--identity]

.. container:: paster-usage

  --version
      how program's version number and exit
  -h, --help
      show this help message and exit
  -p PACKAGE, --package=PACKAGE
      package name for the code
  --dry-run
      dry run (don't actually do anything)
  -t TEMPLATES, --templates=TEMPLATES
      user specific templates
  -s, --sqlalchemy
      use SQLAlchemy instead of SQLObject
  -o, --sqlobject
      use SQLObject instead of SQLAlchemy
  -e, --elixir
      use Elixir instead of SQLAlchemy
  -i, --identity
      provide Identity support
"""

import pkg_resources
import re
import optparse
from paste.script import command
from paste.script import create_distro
import os
import stat
import sys

beginning_letter = re.compile(r"^[^a-z]*")
valid_only = re.compile(r"[^a-z0-9_]")

class QuickstartCommand(command.Command):
    """Create a new TurboGears 2 project.

Create a new Turbogears project with this command.

Example usage::

    $ paster quickstart yourproj

or start project with elixir::

    $ paster quickstart -e yourproj
    """

    version = pkg_resources.get_distribution('turbogears2').version
    max_args = 3
    min_args = 0
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__
    group_name = "TurboGears2"
    name = None
    package = None
    dry_run = False
    templates = "turbogears2"
    svn_repository = None
    sqlalchemy = False
    sqlobject = False
    elixir = False
    identity = False

    parser = command.Command.standard_parser(quiet=True)
    parser = optparse.OptionParser(
                    usage="%prog quickstart [options] [project name]",
                    version="%prog " + version)
    parser.add_option("-s", "--sqlalchemy",
            help="use SQLAlchemy instead of SQLObject",
            action="store_true", dest="sqlalchemy", default = True)
    parser.add_option("-o", "--sqlobject",
            help="use SQLObject instead of SQLAlchemy",
            action="store_true", dest="sqlobject", default = False)
    parser.add_option("-e", "--elixir",
            help="use SQLAlchemy Elixir instead of SQLObject",
            action="store_true", dest="elixir", default = False)
#    parser.add_option("-i", "--identity",
#            help="provide Identity support",
#            action="store_true", dest="identity", default = False)
    parser.add_option("-p", "--package",
            help="package name for the code",
            dest="package")
    parser.add_option("-t", "--templates",
            help="user specific templates",
            dest="templates", default = templates)
    parser.add_option("-r", "--svn-repository", metavar="REPOS",
            help="create project in given SVN repository",
            dest="svn_repository", default = svn_repository)
    parser.add_option("--dry-run",
            help="dry run (don't actually do anything)",
            action="store_true", dest="dry_run")

    def command(self):
        """Quickstarts the new project."""

        self.__dict__.update(self.options.__dict__)

        if not True in [self.elixir, self.sqlalchemy, self.sqlobject]:
            self.sqlalchemy = True
        if self.elixir:
            self.sqlalchemy = True

        if self.args:
            self.name = self.args[0]

        while not self.name:
            self.name = raw_input("Enter project name: ")

        while not self.package:
            package = self.name.lower()
            package = beginning_letter.sub("", package)
            package = valid_only.sub("", package)
            self.package = raw_input("Enter package name [%s]: " % package)
            if not self.package:
                self.package = package

        doidentity = self.identity
        """while not doidentity:
            doidentity = raw_input("Do you need Identity "
                        "(usernames/passwords) in this project? [no] ")
            doidentity = doidentity.lower()
            if not doidentity or doidentity.startswith('n'):
                self.identity="none"
                break
            if doidentity.startswith("y"):
                doidentity = True
                break
            print "Please enter y(es) or n(o)."
            doidentity = None

        if doidentity is True:
            if self.sqlalchemy:
                self.identity = "sqlalchemy"
            else:
                self.identity = "sqlobject"
        """
        self.name = pkg_resources.safe_name(self.name)

        env = pkg_resources.Environment()
        if self.name.lower() in env:
            print 'The name "%s" is already in use by' % self.name,
            for dist in env[self.name]:
                print dist
                return

        import imp
        try:
            if imp.find_module(self.package):
                print 'The package name "%s" is already in use' % self.package
                return
        except ImportError:
            pass

        if os.path.exists(self.name):
            print 'A directory called "%s" already exists. Exiting.' % self.name
            return

        command = create_distro.CreateDistroCommand("create")
        cmd_args = []
        for template in self.templates.split(" "):
            cmd_args.append("--template=%s" % template)
        if self.svn_repository:
            cmd_args.append("--svn-repository=%s" % self.svn_repository)
        if self.dry_run:
            cmd_args.append("--simulate")
            cmd_args.append("-q")
        cmd_args.append(self.name)
        cmd_args.append("sqlalchemy=%s" % self.sqlalchemy)
        cmd_args.append("elixir=%s" % self.elixir)
        cmd_args.append("sqlobject=%s" % self.sqlobject)
        cmd_args.append("identity=%s" % self.identity)
        cmd_args.append("package=%s" % self.package)
        cmd_args.append("tgversion=%s"%self.version)
        # set the exact ORM-version for the proper requirements
        # it's extracted from our own requirements, so looking
        # them up must be in sync (there must be the extras_require named
        # sqlobject/sqlalchemy)
        """if self.sqlobject:
            sqlobjectversion = str(get_requirement('sqlobject'))
            cmd_args.append("sqlobjectversion=%s" % sqlobjectversion)
        if self.sqlalchemy:
            sqlalchemyversion = str(get_requirement('sqlalchemy'))
            cmd_args.append("sqlalchemyversion=%s" % sqlalchemyversion)
        if self.elixir:
            elixirversion = str(get_requirement('future', 'elixir'))
            cmd_args.append("elixirversion=%s" % elixirversion)
        """
        command.run(cmd_args)

        if not self.dry_run:
            os.chdir(self.name)
            if self.sqlobject:
                # Create the SQLObject history directory only when needed.
                # With paste.script it's only possible to skip files, but
                # not directories. So we are handling this manually.
                sodir = '%s/sqlobject-history' % self.package
                if not os.path.exists(sodir):
                    os.mkdir(sodir)
                try:
                    if not os.path.exists(os.path.join(os.path.dirname(
                            os.path.abspath(sodir)), '.svn')):
                        raise OSError
                    command.run_command('svn', 'add', sodir)
                except OSError:
                    pass

            startscript = "start-%s.py" % self.package
            if os.path.exists(startscript):
                oldmode = os.stat(startscript).st_mode
                os.chmod(startscript,
                        oldmode | stat.S_IXUSR)
            sys.argv = ["setup.py", "egg_info"]
            import imp
            imp.load_module("setup", *imp.find_module("setup", ["."]))

            # dirty hack to allow "empty" dirs
            for base, path, files in os.walk("./"):
                for file in files:
                    if file == "empty":
                        os.remove(os.path.join(base, file))
