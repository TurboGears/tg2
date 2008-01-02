"""Quickstart command to generate a new project.

TurboGears 2 uses Paste to create and deploy projects as well as create new 
controllers and their tests.

Quickstart takes the files from turbogears.pastetemplates and processes them to produce
a new, ready-to-run project.

Create a new project named helloworld with this command::

    $ paster quickstart helloworld

You could use TurboGears2, Pylons, and WebHelper paster commands within the project.

Usage: 

.. parsed-literal::

    paster quickstart [--version][-h|--help]
            [-p *PACKAGE*][--dry-run][-t|--templates *TEMPLATES*]
            [-s|--sqlalchemy][-o|--sqlobject][-i|--identity]

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
  -i, --identity
      provide Identity support


"""
import pkg_resources
import re
import optparse
from paste.script import command
from paste.script import templates, create_distro
from tg.pastetemplate import TurboGearsTemplate
import os
import os.path
import stat
import sys

beginning_letter = re.compile(r"^[^a-z]*")
valid_only = re.compile(r"[^a-z0-9_]")

class QuickstartCommand(command.Command):
    """Create a new TurboGears 2 project
Create a new Turbogears project with this command.
    
Example usage::
    
    $ paster quickstart yourproj

or start project with sqlobject::
    
    $ paster quickstart -o yourproj
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
    sqlalchemy = True
    sqlobject = False
    elixir = True
    identity = False
    
    parser = command.Command.standard_parser(quiet=True)
    parser = optparse.OptionParser(
                    usage="%prog quickstart [options] [project name]",
                    version="%prog " + version)
    parser.add_option("-p", "--package", 
            help="package name for the code",
            dest="package")
    parser.add_option("--dry-run", 
            help="dry run (don't actually do anything)",
            action="store_true", dest="dry_run")
    parser.add_option("-t", "--templates", 
            help="user specific templates",
            dest="templates", default = templates)
    parser.add_option("-s", "--sqlalchemy",
            help="use SQLAlchemy instead of SQLObject",
            action="store_true", dest="sqlalchemy", default = True)
    parser.add_option("-o", "--sqlobject",
            help="use SQLObject instead of SQLAlchemy",
            action="store_true", dest="sqlobject", default = False)
    parser.add_option("-e", "--elixir",
            help="use SQLAlchemy Elixir instead of SQLObject",
            action="store_true", dest="elixir", default = True)
    """parser.add_option("-i", "--identity",
            help="provide Identity support",
            action="store_true", dest="identity", default = False)
    """
    def command(self):
        "Quickstarts the new project."
        if not True in [self.elixir, self.sqlalchemy, self.sqlobject]:
            self.sqlobject = True
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
            print "the name %s is already in use by" %self.name,
            for dist in env[self.name]:
                print dist
                return

        import imp
        try:
            if imp.find_module(self.package):
                print "the package name %s is already in use" % self.package
                return
        except ImportError:
            pass

        if os.path.exists(self.name):
            print("A directory called '%s' already exists. Exiting."
                      % self.name)
            return        
            
        
        command = create_distro.CreateDistroCommand("create")
        cmd_args = []
        for template in self.templates.split(" "):
            cmd_args.append("--template=%s" % template)
        cmd_args.append(self.name)
        cmd_args.append("package=%s" % self.package)
        cmd_args.append("identity=%s" % self.identity)
        cmd_args.append("sqlobject=%s" % self.sqlobject)
        cmd_args.append("sqlalchemy=%s" % self.sqlalchemy)
        cmd_args.append("elixir=%s" % self.elixir)
        cmd_args.append("tgversion=%s"%self.version)
        if self.dry_run:
            cmd_args.append("--simulate")
            cmd_args.append("-q")
        command.run(cmd_args)
        
        if not self.dry_run:
            os.chdir(self.name)
            sodir = '%s/sqlobject-history' % self.package
            if self.sqlobject and not os.path.exists(sodir):
                os.mkdir(sodir)
            startscript = "start-%s.py" % self.package
            if os.path.exists(startscript):
                oldmode = os.stat(startscript).st_mode
                os.chmod(startscript, 
                        oldmode | stat.S_IXUSR)
            sys.argv = ["setup.py", "egg_info"]
            import imp
            imp.load_module("setup", *imp.find_module("setup", ["."]))

            # dirty hack to allow "empty" dirs
            for base,path,files in os.walk("./"):
                for file in files:
                    if file  == "empty":
                        os.remove(os.path.join(base, file))
