"""Setup the Wiki-20 application"""
import logging

from paste.deploy import appconfig
from pylons import config

from wiki20.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_config(command, filename, section, vars):
    """Place any commands to setup wiki20 here"""
    conf = appconfig('config:' + filename)
    load_environment(conf.global_conf, conf.local_conf)
    # Load the models
    from wiki20 import model
    print "Creating tables"
    model.metadata.create_all(bind=config['pylons.app_globals'].sa_engine)


    model.DBSession.commit()
    print "Successfully setup"
