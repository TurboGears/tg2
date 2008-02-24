from tg.pastetemplate import TurboGearsTemplate
import os, shutil
import pkg_resources
from paste.deploy import loadapp
from paste.fixture import TestApp
from paste.script.create_distro import CreateDistroCommand

testDataPath=os.path.abspath(os.path.dirname(__file__))+os.sep+'data'

app = None

class MochOptions:
    simulate = False
    overwrite=True

def _setup():
    global app
    command = CreateDistroCommand('name')
    command.verbose = False
    command.simulate = False
    command.options = MochOptions()
    command.interactive=False
    command.create_template(TurboGearsTemplate('TGTest'), testDataPath+'/TGTest', {'package':'TGTest', 'project':'tgtest', 'egg':'tgtest'})
    here_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = testDataPath+'/TGTest'
    
    pkg_resources.working_set.add_entry(proj_dir)
    app = loadapp('config:development.ini', relative_to=proj_dir)
    
def _teardown():
    shutil.rmtree(testDataPath, ignore_errors=True)
    
def _test_app_runs_index():
    resp = app.get('/')
    s =  resp.body
    assert s == '', s
