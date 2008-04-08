"""
TurboGears CRUD interface generator

Once you have created a model, (let's take model object named 
"Movie" for example), you could create a new crud controller
package with this command::

    $ paster crud Movie

Usage:

.. parsed-literal::

    paster crud [-m|--model][-p|--package]
            [-f|--form][-i|--id][--dry-run]

.. container:: paster-usage

  -m, --model
      model name
  -p, --package
      package name
  -f, --form
      form name
  -i, --id
      primary key
  --dry-run
      dry run (don't actually do anything)
"""

from paste.script import command
import optparse
import sys
import os
from paste.script.filemaker import FileOp
from paste.script.pluginlib import find_egg_info_dir

class CrudCommand(command.Command):
    """Generate CRUD interface based on model

    Example usage::

    $ paster crud -i [primary key] [model name] [package name]
    """
    max_args = 4
    min_args = 0
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__
    group_name = "TurboGears2"

    modelname = None
    modelpackage = None
    modelform = None
    templates = "tgcrud2"
    primary_key = None
    base_package = None

    parser = command.Command.standard_parser(quiet=True)
    parser = optparse.OptionParser(
                 usage="paster crud [model name] [package name]")
    parser.add_option("-m", "--model",
            help="class name in the model",
            dest="modelname")
    parser.add_option("-p", "--package",
            help="package name for the code",
            dest="modelpackage")
    parser.add_option("-f", "--form",
            help="form name for model",
            dest="modelform")
    parser.add_option("-i", "--id",
            help="model primary key",
            dest="primary_key")
    parser.add_option("--dry-run",
            help="dry run (don't actually do anything)",
            action="store_true", dest="dry_run")

    def command(self):
        self.modelname = self.options.modelname
        self.modelpackage = self.options.modelpackage
        self.modelform = self.options.modelform
        self.primary_key = self.options.primary_key

        try:
            try:
                # Determine the package name from the .egg-info top_level.txt.
                here_dir = os.getcwd()
                egg_info = find_egg_info_dir(here_dir)
                f = open(os.path.join(egg_info, 'top_level.txt'))
                packages = [l.strip() for l in f.readlines()
                        if l.strip() and not l.strip().startswith('#')]
                f.close()
                #upper 2 levels
                baselink = os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__)))
                file_op = FileOp(
                            source_dir=os.path.join(baselink, 'templates'))
                self.base_package, directory = \
                            file_op.find_dir('controllers', True)
            except:
                raise command.BadCommand('No egg_info directory was found')

        except command.BadCommand, e:
            raise command.BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise command.BadCommand('An unknown error occurred. %s' % msg)

        # parse args
        if self.args:
            self.modelname = self.args[0]
            try:
                self.modelpackage = self.args[1]
            except:
                self.modelpackage = None

        while not self.modelname:
            print "Note: Make sure you have created your models first"
            self.modelname = raw_input("Enter the model name: ")
        while not self.primary_key:
            self.primary_key = raw_input("Enter the primary key [id]: ")
            if not self.primary_key:
                self.primary_key = 'id'
        while not self.modelpackage:
            self.modelpackage = raw_input("Enter the package name [%s]: "
                            % (str(self.modelname.capitalize())+'Controller'))
            if not self.modelpackage:
                self.modelpackage = str(self.modelname.capitalize())+\
                                    'Controller'
        while not self.modelform:
            self.modelform = raw_input("Enter the model form name [%s]: "
                                % (str(self.modelname.capitalize())+'Form'))
            if not self.modelform:
                self.modelform = self.modelname.capitalize()

        #check for lib name conflict
        #print self.primary_key
        # Setup the controller
        self.modelpackageLower = self.modelpackage.lower()
        self.modelnameLower = self.modelname.lower()
        file_op.template_vars.update(
                {'package': self.base_package,
                 'modelname': self.modelname,
                 'modelnameLower': self.modelnameLower,
                 'modelpackage': self.modelpackage,
                 'modelpackageLower': self.modelpackageLower,
                 'id': self.primary_key})
        file_op.copy_file(template='crud_controller.py_tmpl',
                         dest=os.path.join('controllers', directory),
                         filename=self.modelpackage.lower())
        file_op.copy_file(template='crud_form_widget.py_tmpl',
                         dest=os.path.join('controllers', directory),
                         filename=self.modelname.lower()+'form')
        #setup templates
        templatepath = file_op.find_dir('templates', True)[1]
        #print templatepath
        #print "create dir:",
        #    os.path.join(templatepath, self.modelpackageLower)
        if not os.path.exists(os.path.join(templatepath,
                                self.modelpackageLower)):
            #print "create dir:", self.modelpackageLower
            os.mkdir(os.path.join(templatepath, self.modelpackageLower))

        #print os.path.join(templatepath, self.modelpackage)
        file_op.copy_file(template='crud/__init__.py_tmpl',
                         dest=os.path.join(templatepath,
                                            self.modelpackageLower),
                         filename='__init__')
        file_op.copy_file(template='crud/list.html_tmpl',
                         dest=os.path.join(templatepath,
                                            self.modelpackageLower),
                         filename='list.html',
                         add_py=False)
        file_op.copy_file(template='crud/show.html_tmpl',
                         dest=os.path.join(templatepath,
                                            self.modelpackageLower),
                         filename='show.html',
                         add_py=False)
        file_op.copy_file(template='crud/new_form.html_tmpl',
                         dest=os.path.join(templatepath,
                                            self.modelpackageLower),
                         filename='new_form.html',
                         add_py=False)
        file_op.copy_file(template='crud/edit_form.html_tmpl',
                         dest=os.path.join(templatepath,
                                            self.modelpackageLower),
                         filename='edit_form.html',
                         add_py=False)
