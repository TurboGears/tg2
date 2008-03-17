"""Setup the tgtest application"""
import logging

from paste.deploy import appconfig
from pylons import config

from TGTest.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_config(command, filename, section, vars):
    """Place any commands to setup TGTest here"""
    conf = appconfig('config:' + filename)
    load_environment(conf.global_conf, conf.local_conf)

    # create model
    from TGTest import model
    print "Creating tables"
    model.metadata.create_all(bind=config['pylons.g'].sa_engine)
    model.DBSession.commit()

    print "Successfully setup"
