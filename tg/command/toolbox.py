"""Commands to start Toolbox"""
from base import CommandWithDB
import optparse
from turbogears.util import get_project_config, get_package_name
import sys
import turbogears
from turbogears.identity import SecureObject,from_any_host

class ToolboxCommand(CommandWithDB):

    desc = "Launch the TurboGears Toolbox"

    def __init__(self, version):
        self.hostlist = ['127.0.0.1','::1']

        parser = optparse.OptionParser(
            usage="%prog toolbox [options]", version="%prog " + version)
        parser.add_option("-n", "--no-open",
                 help="don't open browser automatically",
                 dest="noopen", action="store_true",
                 default=False)
        parser.add_option("-c", "--add-client",
                help="allow the client ip address specified to connect to toolbox (Can be specified more than once)",
                dest="host", action="append", default=None)
        parser.add_option("-p", "--port",
                help="port to run the Toolbox on", dest="port", default=7654)
        parser.add_option("--conf", help="config file to use", dest="config", default=get_project_config())
        (options, args) = parser.parse_args(sys.argv[1:])
        self.port = int(options.port)
        self.noopen = options.noopen
        self.config = options.config
        if options.host:
            self.hostlist = self.hostlist + options.host
        turbogears.widgets.load_widgets()


    def openbrowser(self):
        import webbrowser
        webbrowser.open("http://localhost:%d" % self.port)

    def run(self):
        import cherrypy
        from turbogears import toolbox

        try:
            if get_package_name():
                conf = turbogears.config.config_obj( configfile = self.config,
                        modulename="%s.config" % get_package_name() )
            else:
                conf = turbogears.config.config_obj( configfile = self.config )
            
            new_conf = {}
            for key in ( "sqlobject.dburi", "sqlalchemy.dburi", "visit.on", "visit.manager", "visit.saprovider.model", 
                    "identity.provider", "identity.saprovider.model.group", "identity.saprovider.model.permission",
                    "identity.saprovider.model.user", "identity.saprovider.model.visit", "identity.on"):
                new_conf[key] = conf.get("global").get(key, None) 
            turbogears.config.update({"global" : new_conf})

        except AttributeError, e:
            pass

        root = SecureObject(toolbox.Toolbox(),from_any_host(self.hostlist), exclude=['noaccess'])

        cherrypy.tree.mount(root, "/")

        turbogears.config.update({"global" : {
            "server.socket_port" : self.port,
            "server.environment" : "development",
            "server.log_to_screen" : True,
            "i18n.run_template_filter" : True, 
            "autoreload.on" : False,
            "server.package" : "turbogears.toolbox",
            "log_debug_info_filter.on" : False,
            "identity.failure_url" : "/noaccess"
            }})

        if not self.noopen:
            cherrypy.server.start_with_callback(self.openbrowser)
        else:
            cherrypy.server.start()
