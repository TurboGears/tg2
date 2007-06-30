"Commands for the TurboGears command line tool."
import optparse
import sys
import os
import pkg_resources
import tg
from tg.util import load_project_config, get_project_config


sys.path.insert(0, os.getcwd())


def silent_os_remove(fname):
    """
    Tries to remove file FNAME but mutes any error that may happen.

    Returns True if file was actually removed and false otherwise
    """
    try:
        os.remove(fname)
        return True
    except os.error:
        pass
    return False

class CommandWithDB(object):
    "Base class for commands that need to use the database"
    config = None

    def __init__(self, version):
        pass

    def find_config(self):
        """Chooses the config file, trying to guess whether this is a
        development or installed project."""
        load_project_config(self.config)
        self.dburi = turbogears.config.get("sqlobject.dburi", None)
        if self.dburi and self.dburi.startswith("notrans_"):
            self.dburi = self.dburi[8:]

commands = None

def main():
    "Main command runner. Manages the primary command line arguments."
    # add commands defined by entrypoints
    commands = {}
    for entrypoint in pkg_resources.iter_entry_points("turbogears.command"):
        command = entrypoint.load()
        commands[entrypoint.name] = (command.desc, entrypoint)
  
    def _help():
        "Custom help text for tg-admin."

        print """
TurboGears %s command line interface

Usage: %s [options] <command>

Options:
    -c CONFIG --config=CONFIG    Config file to use
    -e EGG_SPEC --egg=EGG_SPEC   Run command on given Egg

Commands:""" % (turbogears.__version__, sys.argv[0])

        longest = max([len(key) for key in commands.keys()])
        format = "%" + str(longest) + "s  %s"
        commandlist = commands.keys()
        commandlist.sort()
        for key in commandlist:
            print format % (key, commands[key][0])


    parser = optparse.OptionParser()
    parser.allow_interspersed_args = False
    parser.add_option("-c", "--config", dest="config")
    parser.add_option("-e", "--egg", dest="egg")
    parser.print_help = _help
    (options, args) = parser.parse_args(sys.argv[1:])

    # if not command is found display help
    if not args or not commands.has_key(args[0]):
        _help()
        sys.exit()

    commandname = args[0]
    # strip command and any global options from the sys.argv
    sys.argv = [sys.argv[0],] + args[1:]
    command = commands[commandname][1]
    command = command.load()
    
    if options.egg:
        egg = pkg_resources.get_distribution(options.egg)
        os.chdir(egg.location)

    if hasattr(command,"need_project"):
        if not turbogears.util.get_project_name():
            print "This command needs to be run from inside a project directory"
            return
        elif not options.config and not os.path.isfile(get_project_config()):
            print """No default config file was found.
If it has been renamed use:
tg-admin --config=<FILE> %s""" % commandname
            return
    command.config = options.config
    command = command(turbogears.__version__)
    command.run()

__all__ = ["main"]
