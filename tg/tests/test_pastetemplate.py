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
    templates=['turbogears2',]
    output_dir=testDataPath
    list_templates=False
    list_variables=False
    config=None
    inspect_files=False
    svn_repository=False

def setup():
    global app
    command = CreateDistroCommand('name')
    command.verbose = False
    command.simulate = False
    command.options = MochOptions()
    command.interactive=False
    command.args=['TGTest',]
#    command.templates = TurboGearsTemplate('TGTest')
#    command.create_template(TurboGearsTemplate('TGTest'), testDataPath+'/TGTest', {'package':'TGTest', 'project':'tgtest', 'egg':'tgtest'})
    command.command()
#    here_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = testDataPath+'/TGTest'
    
    pkg_resources.working_set.add_entry(proj_dir)
    app = loadapp('config:development.ini', relative_to=proj_dir)
    app = TestApp(app)

def teardown():
    shutil.rmtree(testDataPath, ignore_errors=True)
    
def _test_app_runs_index():
    resp = app.get('/')
    s =  resp.body
    assert """<h2>Getting help</h2>
      <ul class="links">
        <li><a href="http://docs.turbogears.org/2.0">Documentation</a></li>
        <li><a href="http://docs.turbogears.org/2.0/API">API Reference</a></li>
        <li><a href="http://trac.turbogears.org/turbogears/">Bug Tracker</a></li>
        <li><a href="http://groups.google.com/group/turbogears">Mailing
        List</a></li>
      </ul>""" in s, s
