from tg.configuration import AppConfig, Bunch
import formstutorial
from formstutorial import model
from formstutorial.lib import app_globals, helpers

base_config = AppConfig()
base_config.renderers = []

base_config.package = formstutorial

#Set the default renderer
base_config.default_renderer = 'genshi'
base_config.renderers.append('genshi') 

#Configure the base SQLALchemy Setup
base_config.use_sqlalchemy = True
base_config.model = formstutorial.model
base_config.DBSession = formstutorial.model.DBSession

