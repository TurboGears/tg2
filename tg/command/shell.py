from base import CommandWithDB
from turbogears import config, database
from turbogears.util import get_model

class Shell(CommandWithDB):
    """Convenient version of the Python interactive shell.
    This shell attempts to locate your configuration file and model module
    so that it can import everything from your model and make it available
    in the Python shell namespace."""

    desc = "Start a Python prompt with your database available"
    need_project = True

    def run(self):
        "Run the shell"
        self.find_config()
        
        mod = get_model()
        if mod:
            locals = mod.__dict__
        else:
            locals = dict(__name__="tg-admin")
            
        if config.get("sqlalchemy.dburi"):
            using_sqlalchemy = True
            database.bind_meta_data()
            locals.update(session=database.session,
                          metadata=database.metadata)
        else:
            using_sqlalchemy = False

        try:
            # try to use IPython if possible
            import IPython

            class CustomIPShell(IPython.iplib.InteractiveShell):
                def raw_input(self, *args, **kw):
                    try:
                        return \
                         IPython.iplib.InteractiveShell.raw_input(self,
                                                    *args, **kw)
                    except EOFError:

                        b = raw_input("Do you wish to commit your "
                                      "database changes? [yes]")
                        if not b.startswith("n"):
                            if using_sqlalchemy:
                                self.push("session.flush()")
                            else:
                                self.push("hub.commit()")
                        raise EOFError

            shell = IPython.Shell.IPShell(user_ns=locals,
                                          shell_class=CustomIPShell)
            shell.mainloop()
        except ImportError:
            import code

            class CustomShell(code.InteractiveConsole):
                def raw_input(self, *args, **kw): 
                    try:
                        import readline
                    except ImportError:
                        pass

                    try:
                        return code.InteractiveConsole.raw_input(self,
                                                        *args, **kw)
                    except EOFError:
                        b = raw_input("Do you wish to commit your "
                                    "database changes? [yes]")
                        if not b.startswith("n"):
                            if using_sqlalchemy:
                                self.push("session.flush()")
                            else:
                                self.push("hub.commit()")
                        raise EOFError

            shell = CustomShell(locals=locals)
            shell.interact()
