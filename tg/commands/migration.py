"""
TurboGears migration

"""

from paste.script import command
import os
import ConfigParser
from migrate.versioning.shell import main

class MigrateCommand(command.Command):
    """Sqlalchemy migration"""
    max_args = 3
    min_args = 1
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__
    group_name = "TurboGears2"

    parser = command.Command.standard_parser(verbose=True)

    def command(self):
        ini = 'development.ini'
        sect = 'app:main'
        option = 'sqlalchemy.url'

        # get sqlalchemy.url config in app:mains
        curdir = os.getcwd()
        conf = ConfigParser.ConfigParser()
        conf.read(os.path.join(curdir, ini))

        self.name = "migration"
        try:
            self.dburi = conf.get(sect, option, vars={'here':curdir})
        except:
            print "you shold set sqlalchemy.url in development.ini first"

        print "The repository is %s\nThe dburi is in %s"%(self.name, self.dburi)
        main(argv=self.args, url=self.dburi,repository=self.name, name=self.name)
