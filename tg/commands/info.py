"""
TurboGears related projects and their versions
"""
import pkg_resources
from paste.script import command

entrypoints = {"TurboGears2 Commands" : "turbogears2.command",
    "Template Engines" : "python.templating.engines",
    "TurboGears2 Templates": "turbogears2.template",
    "Widget Packages" : "toscawidgets.widgets",
    "Toolbox2 Gadgets" : "turbogears2.toolboxcommand",
}
"""#elements that not clear yet
    "TurboGears2 Extensions" : "turbogears2.extensions",
    "Auth Providers" : "turbogears2.auth.provider",
    "Visit Managers" : "turbogears2.visit.manager",
"""


def retrieve_info():
    packages=['%s' % i for i in pkg_resources.require("TurboGears2")]
    plugins = {}
    for name, pointname in entrypoints.items():
        if name in "samples":
            pass
        else:
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
        print """TurboGears2 Complete Version Information"""
        print """========================================"""
        print "\nTurboGears2 requires:\n"
        li = []
        packages, plugins = retrieve_info()
        for p in packages:
            li.append(p)
        # print dependent modules
        for p in list(set(li)):
            print '  *', p
        # print plugins
        for name, pluginlist in plugins.items():
            print "\n", name, "\n"
            for plugin in pluginlist:
                print '  *', plugin

        # print widgets
        print "\nAvailable Widgets:\n"
        for entrypoint in pkg_resources.iter_entry_points('toscawidgets.widgets'):
            if entrypoint.name in "samples":
                pass
            else:
                tool = entrypoint.load()
                temp = dir(tool)
                print "\n  * "+str(entrypoint.dist)+":"
                for t in temp:
                    if not t.startswith('__'):
                        print '    -', t

