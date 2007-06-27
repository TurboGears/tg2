import os.path
import dispatch
from turbogears import config
from turbogears.util import get_model, get_project_name
from base import CommandWithDB
import sys
import optparse
import glob
import pkg_resources

no_connection_param = ["help", "list"]
no_model_param = ["help"]

[dispatch.generic()]
def sacommand(command, args):
    pass

[sacommand.when("command == 'help'")]
def sahelp(command, args):
    print """TurboGears SQLAlchemy Helper

help    this display
create  create the database tables
"""
[sacommand.when("command == 'create'")]
def sacreate(command, args):
    print "Creating tables at %s" % (config.get("sqlalchemy.dburi"))
    from turbogears.database import bind_meta_data, metadata
    bind_meta_data()
    get_model()
    metadata.create_all()
    
class SQL(CommandWithDB):
    """
    Wrapper command for sqlobject-admin, and provide some sqlalchemy support.

    This automatically supplies sqlobject-admin with the database that
    is found in the config file. Will also supply the model module as
    appropriate."""

    desc = "Run the database provider manager"
    need_project = True

    def __init__(self, version):
        if len(sys.argv) == 1 or sys.argv[1][0] == "-":
            parser = optparse.OptionParser(
                usage="%prog sql [command]\n\n" \
                      "hint: '%prog sql help' will list the sqlobject " \
                      "commands",
                version="%prog " + version)
            parser.add_option("-c", "--config", help="config file",
                              dest="config")
            (options, args) = parser.parse_args(sys.argv[1:3])

            if not options.config:
                parser.error("Please provide a valid option or command.")
            self.config = options.config
            # get rid of our config option
            if not args:
                del sys.argv[1:3]
            else:
                del sys.argv[1]

        self.find_config()

    def run(self):
        "Executes the sqlobject-admin code."
        if not "--egg" in sys.argv and not get_project_name():
            print "this don't look like a turbogears project"
            return
        else:
            command = sys.argv[1]
            
            if config.get("sqlalchemy.dburi"):
                try:
                    sacommand(command, sys.argv)
                except dispatch.interfaces.NoApplicableMethods:
                    sacommand("help", [])
                return

            sqlobjcommand = command    
            if sqlobjcommand not in no_connection_param:
                if not self.dburi:
                    print """Database URI not specified in the config file (%s).
        Please be sure it's on the command line.""" % self.config
                else:
                    print "Using database URI %s" % self.dburi
                    sys.argv.insert(2, self.dburi)
                    sys.argv.insert(2, "-c")

            if sqlobjcommand not in no_model_param:
                if not "--egg" in sys.argv:
                    eggname = glob.glob("*.egg-info")
                    if not eggname or not \
                        os.path.exists(os.path.join(eggname[0], "sqlobject.txt")):
                        eggname = self.fix_egginfo(eggname)
                    eggname = eggname[0].replace(".egg-info", "")
                    if not "." in sys.path:
                        sys.path.append(".")
                        pkg_resources.working_set.add_entry(".")
                    sys.argv.insert(2, eggname)
                    sys.argv.insert(2, "--egg")

            from sqlobject.manager import command
            command.the_runner.run(sys.argv)

    def fix_egginfo(self, eggname):
        print """
This project seems incomplete. In order to use the sqlobject commands
without manually specifying a model, there needs to be an
egg-info directory with an appropriate sqlobject.txt file.

I can fix this automatically. Would you like me to?
"""
        dofix = raw_input("Enter [y] or n: ")
        if not dofix or dofix.lower()[0] == 'y':
            oldargs = sys.argv
            sys.argv = ["setup.py", "egg_info"]
            import imp
            imp.load_module("setup", *imp.find_module("setup", ["."]))
            sys.argv = oldargs

            import setuptools
            package = setuptools.find_packages()[0]
            eggname = glob.glob("*.egg-info")
            sqlobjectmeta = open(os.path.join(eggname[0], "sqlobject.txt"), "w")
            sqlobjectmeta.write("""db_module=%(package)s.model
history_dir=$base/%(package)s/sqlobject-history
""" % dict(package=package))
        else:
            sys.exit(0)
        return eggname
