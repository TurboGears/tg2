import pkg_resources

entrypoints = {"tg-admin Commands" : "turbogears.command",
    "Template Engines" : "python.templating.engines", 
    "Widget Packages" : "turbogears.widgets", 
    "TurboGears Extensions" : "turbogears.extensions",
    "Identity Providers" : "turbogears.identity.provider",
    "Visit Managers" : "turbogears.visit.manager",
    "Toolbox Plugins" : "turbogears.toolboxcommand"}

def retrieve_info():
    packages=['%s' % i for i in pkg_resources.require("Turbogears")]
    plugins = {}
    for name, pointname in entrypoints.items():
        plugins[name] = ["%s (%s)" % (entrypoint.name, str(entrypoint.dist))
            for entrypoint in pkg_resources.iter_entry_points(pointname)
        ]
    return packages, plugins

class InfoCommand:
    """Shows version info for debuging"""

    desc = "Show version info"

    def __init__(self,*args, **kwargs):
        pass

    def run(self):
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
