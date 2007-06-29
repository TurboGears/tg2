"""Quickstart command to generate a new project.

Quickstart takes the files from turbogears.quickstart and processes them to produce
a new, ready-to-run project.

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

class quickstart(command.Command):
    """
    Implementation of quickstart.
    
    """
    version = pkg_resources.get_distribution('turbogears2').version
    max_args = 3
    min_args = 0
    usage = "paster quickstart [options] [project name]"
    summary = "Create a new TurboGears project"
    group_name = "TurboGears2"
    
    name = None
    package = None
    dry_run = False
    templates = "turbogears2"
    sqlalchemy = True
    sqlobject = False
    identity = False
    
    parser = command.Command.standard_parser(verbose=True)
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
    parser.add_option("-i", "--identity",
            help="provide Identity support",
            action="store_true", dest="identity", default = False)
    
    def command(self):
        "Quickstarts the new project."
        if self.args:
            self.name = self.args[0]

        if self.sqlobject:
            self.sqlalchemy = False

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
        while not doidentity:
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
        cmd_args.append("sqlalchemy=%s" % self.sqlalchemy)
        if self.dry_run:
            cmd_args.append("--simulate")
            cmd_args.append("-q")
        command.run(cmd_args)
        
        if not self.dry_run:
            os.chdir(self.name)
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

#class update:
#    "Implementation of update"
#    
#    desc = "Update an existing turbogears project"
#    need_project = True
#    
#    name = None
#    templates = "turbogears"
#    identity = False
#    sqlalchemy = False
#    
#    def __init__(self, version):
#        parser = optparse.OptionParser(usage="%prog quickstart [options]",
#                                       version="%prog " + version)
#        parser.add_option("-t", "--templates", help="user specific templates",
#            dest="templates", default=self.templates)
#        parser.add_option("-s", "--sqlalchemy",
#            help="use SQLAlchemy instead of SQLObject",
#            action="store_true", dest="sqlalchemy", default = False)
#        parser.add_option("-i", "--identity",
#            help="provide Identity support",
#            action="store_true", dest="identity", default = False)
#        (options, args) = parser.parse_args()
#        self.__dict__.update(options.__dict__)
#        self.turbogearsversion = version
#
#    def run(self):
#        "Updates an existing project"
#        self.name = turbogears.util.get_project_name()
#        self.package = turbogears.util.get_package_name()
#        turbogears.command.base.load_project_config()
#        if not self.sqlalchemy:
#            if turbogears.config.get('sqlalchemy.dburi'):
#                self.sqlalchemy = True 
#        if not self.identity:
#            if turbogears.config.get('identity.on'):
#                self.identity = True
#        if self.identity:
#            if self.sqlalchemy:
#                self.identity = 'sqlalchemy'
#            else:
#                self.identity =  'sqlobject'
#        else:
#            self.identity = 'none'
#        currentdir = os.path.basename(os.getcwd())
#        if not currentdir == self.name:
#            print 'it looks like your project dir "%s" is named wrongly. Please rename it to "%s"' %(currentdir, self.name)
#            return
#        
#        command = create_distro.CreateDistroCommand("create")
#        cmd_args = []
#        cmd_args.append("-o../")
#        for template in self.templates.split(" "):
#            cmd_args.append("--template=%s" % template)
#        cmd_args.append(self.name)
#        cmd_args.append("package=%s" %self.package)
#        cmd_args.append("identity=%s" %self.identity)
#        cmd_args.append("sqlalchemy=%s" %self.sqlalchemy)
#        command.run(cmd_args)
#
#        startscript = "start-%s.py" % self.package
#        if os.path.exists(startscript):
#            oldmode = os.stat(startscript).st_mode
#            os.chmod(startscript, 
#                    oldmode | stat.S_IXUSR)
#        sys.argv = ["setup.py", "egg_info"]
#        import imp
#        imp.load_module("setup", *imp.find_module("setup", ["."]))
#        
#        # dirty hack to allow "empty" dirs
#        for base,path,files in os.walk("./"):
#            for file in files:
#                if file  == "empty":
#                    os.remove(os.path.join(base, file))

