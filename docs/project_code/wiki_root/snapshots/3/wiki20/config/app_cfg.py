from tg.config import AppConfig, Bunch
from tg.environment import make_load_environment
import wiki20
from wiki20 import model
from wiki20.lib import app_globals, helpers

base_config = AppConfig()
base_config.renderers = []

base_config.package = wiki20

#Set the default renderer
base_config.default_renderer = 'genshi'
base_config.renderers.append('genshi') 

#Configure the base SQLALchemy Setup
base_config.use_sqlalchemy = True
base_config.model = wiki20.model
