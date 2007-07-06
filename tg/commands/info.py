"""
TurboGears related projects and their versions
"""
import pkg_resources
from paste.script import command

entrypoints = {"TurboGears Commands" : "turbogears2.command",
    "Template Engines" : "python.templating.engines", 
    "TurboGears Templates": "turbogears2.template",
    "Toolbox Gadgets" : "turbogears2.toolboxcommand",
}
"""
    "Widget Packages" : "turbogears.widgets", 
    "TurboGears Extensions" : "turbogears.extensions",
    "Identity Providers" : "turbogears.identity.provider",
    "Visit Managers" : "turbogears.visit.manager",
    
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
    """show related projects and their versions"""
    max_args = 0
    min_args = 0
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__
    group_name = "TurboGears2"

    parser = command.Command.standard_parser(verbose=True)
    
    def command(self):
        print """TurboGears Complete Version Information

TurboGears requires:
"""
        packages, plugins = retrieve_info()
        for p in packages:
            print '*', p
        for name, pluginlist in plugins.items():
            print "\n", name, "\n"
            for plugin in pluginlist:
                print '*', plugin
