"""TurboGears2 helpers for setting up your application enviroment

The intention of this module is to provie some helpers that setup sane defaults 
for TG2 applications.  The gaoal is to make the config files smaller, simpler and easier to read. 
"""

from pylons import config
from routes import Mapper

def make_default_route_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                always_scan=config['debug'])
                
    ## Replace the next line with your overides.   Overides should generally come
    ## bevore the default route defined below
    
    # map.connect('overide/url/here', controller='mycontrller', action='send_stuff')
    
    # This route connects your root controller
    map.connect('*url', controller='root', action='route')

    return map