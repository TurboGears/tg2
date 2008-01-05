"""
TurboGears related projects and their versions
"""
import pkg_resources
from paste.script import command

entrypoints = {"TurboGears2 Commands" : "turbogears2.command",
    "Template Engines" : "python.templating.engines",
    "TurboGears2 Templates": "turbogears2.template",
    "Widget Packages" : "toscawidgets.widgets",
}
"""#elements that not clear yet
    "Toolbox Gadgets" : "turbogears2.toolboxcommand",
    "TurboGears2 Extensions" : "turbogears2.extensions",
    "Identity Providers" : "turbogears2.identity.provider",
    "Visit Managers" : "turbogears2.visit.manager",

"""

def retrieve_info():
    packages=['%s' % i for i in pkg_resources.require("TurboGears2")]
    plugins = {}
    for name, pointname in entrypoints.items():
        plugins[name] = ["%s (%s)" % (entrypoint.name, str(entrypoint.dist))
            for entrypoint in pkg_resources.iter_entry_points(pointname)
        ]
    return packages, plugins

class InfoCommand(command.Command):
    """Show TurboGears 2 related projects and their versions"""
    max_args = 0
    min_args = 0
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__
    group_name = "TurboGears2"

    parser = command.Command.standard_parser(verbose=True)

    def command(self):
        print """TurboGears2 Complete Version Information

TurboGears2 requires:
"""
        packages, plugins = retrieve_info()
        for p in packages:
            print '*', p
        for name, pluginlist in plugins.items():
            print "\n", name, "\n"
            for plugin in pluginlist:
                print '*', plugin
