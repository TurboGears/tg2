"""Pylons environment configuration"""
import os
from pylons import config
from pylons.i18n import ugettext
from genshi.filters import Translator
from tg import defaults


def make_load_environment(base_config):

    def load_environment(global_conf, app_conf):
        """Configure the Pylons environment via the ``pylons.config``
        object
        """
        # Pylons paths
        root = os.path.dirname(os.path.abspath(
                base_config.package.__file__))
        paths = dict(root=root,
                     controllers=os.path.join(root, 'controllers'),
                     static_files=os.path.join(root, 'public'),
                     templates=[os.path.join(root, 'templates')])
                     
        # Initialize config with the basic options
        config.init_app(global_conf, app_conf, 
                        package=base_config.package.__name__,
                        paths=paths)
        
                
        # This setups up a set of default route that enables a standard
        # TG2 style object dispatch.   Fell free to overide it with
        # custom routes.  
        make_map = defaults.make_default_route_map
        config['routes.map'] = make_map()
        config['pylons.app_globals'] = base_config.package.lib.app_globals.Globals()
        config['pylons.h'] = base_config.package.lib.helpers
    
        if base_config.auth_backend == "sqlalchemy":        
            config['identity'] = {'user_class':base_config.model.User, 
                                  'group_class':base_config.model.Group, 
                                  'permission_class':base_config.model.Permission,
                                  'users_table':'tg_user',
                                  'groups_table':'tg_group',
                                  'permissions_table':'tg_permission',
                                  'password_encryption_method':'sha',
                          }
    

    
        if 'mako' in base_config.renderers:
        # Create the Mako TemplateLookup, with the default auto-escaping
            from mako.lookup import TemplateLookup
            from tg.render import render_mako
            
            config['pylons.app_globals'].mako_lookup = TemplateLookup(
                directories=paths['templates'],
                module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from webhelpers.html import escape'],
                default_filters=['escape'])
            config['pylons.app_globals'].renderer_functions = render_mako
        
        
        if 'genshi' in base_config.renderers:
            # Create the Genshi TemplateLoader
            from genshi.template import TemplateLoader
            from tg.render import render_genshi
            
            def template_loaded(template):
                "Plug-in our i18n function to Genshi."
                genshi.template.filters.insert(0, Translator(ugettext))
                
            config['pylons.app_globals'].genshi_loader = TemplateLoader(
                paths['templates'], auto_reload=True)
            
            config['pylons.app_globals'].renderer_functions = render_genshi  
                
        if 'jinja' in base_config.renderers:
            # Create the Jinja Environment
            from jinja import ChoiceLoader, Environment, FileSystemLoader
            from tg.render import render_jinja
            
            config['pylons.app_globals'].jinja_env = Environment(loader=ChoiceLoader(
                    [FileSystemLoader(path) for path in paths['templates']]))
            # Jinja's unable to request c's attributes without strict_c
            config['pylons.strict_c'] = True
            
            config['pylons.app_globals'].renderer_functionsloa = render_jinja
        
        # If you'd like to change the default template engine used to render
        # text/html content, edit these options.
        config['buffet.template_engines'].pop()
        template_location = '%s.templates' %base_config.package.__name__
        config.add_template_engine(base_config.default_renderer, 
                                   template_location,  {})

        if base_config.use_sqlalchemy:  
            # Setup SQLAlchemy database engine
            from sqlalchemy import engine_from_config
            engine = engine_from_config(config, 'sqlalchemy.')
            config['pylons.app_globals'].sa_engine = engine
            # Pass the engine to initmodel, to be able to introspect tables
            base_config.package.model.init_model(engine)
            base_config.package.model.DBSession.configure(bind=engine)
            base_config.package.model.metadata.bind = engine

    
        # CONFIGURATION OPTIONS HERE (note: all config options will override
        # any Pylons config options)
    return load_environment 