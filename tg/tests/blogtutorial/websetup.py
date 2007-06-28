import paste.deploy

def setup_config(command, filename, section, vars):
    """
    Place any commands to setup blogtutorial here.
    """
    conf = paste.deploy.appconfig('config:' + filename)
    conf.update(dict(app_conf=conf.local_conf, global_conf=conf.global_conf))
    paste.deploy.CONFIG.push_process_config(conf)

