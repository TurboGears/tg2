"""Simple AppSetup helper class"""
from pylons import config

class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return  dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

class AppConfig(Bunch):
    """Class to store application configuration
    
    This class should have configuration/setup information 
    that is NESSISARY for proper application function.  
    Deployment specific configuration information should go in 
    the config files (eg: development.ini or production.ini." 
    """
    
    def __init__(self):
        self.stand_alone = True
        self.default_renderer = 'genshi'
        self.auth_backend = None 
    
    pass
