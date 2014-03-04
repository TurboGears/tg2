from __future__ import absolute_import

from os.path import exists, getmtime
from tg.i18n import ugettext, ungettext
from tg.render import cached_template
from markupsafe import Markup
from .base import RendererFactory

try:
    import jinja2
except ImportError:  # pragma: no cover
    jinja2 = None

if jinja2 is not None:
    from jinja2.loaders import FileSystemLoader
    from jinja2 import ChoiceLoader, Environment
    from jinja2.filters import FILTERS
    from jinja2.exceptions import TemplateNotFound
else:  # pragma: no cover
    class FileSystemLoader(object): pass

__all__ = ['JinjaRenderer']


class JinjaRenderer(RendererFactory):
    engines = {'jinja': {'content_type': 'text/html'}}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for Jinja2 templates."""
        if jinja2 is None:  # pragma: no cover
            return None

        if config.get('use_dotted_templatenames', True):
            TemplateLoader = DottedTemplateLoader
            template_loader_args = {'dotted_finder': app_globals.dotted_filename_finder}
        else:
            TemplateLoader = FileSystemLoader
            template_loader_args = {}

        if not 'jinja_extensions' in config:
            config.jinja_extensions = []

        # Add i18n extension by default
        if not "jinja2.ext.i18n" in config.jinja_extensions:
            config.jinja_extensions.append("jinja2.ext.i18n")

        if not 'jinja_filters' in config:
            config.jinja_filters = {}

        loader = ChoiceLoader(
            [TemplateLoader(path, **template_loader_args) for path in config.paths['templates']])

        jinja2_env = Environment(loader=loader, autoescape=True,
                                 auto_reload=config.auto_reload_templates,
                                 extensions=config.jinja_extensions)

        # Try to load custom filters module under app_package.lib.templatetools
        try:
            if not config.package_name:
                raise AttributeError()

            filter_package = config.package_name + ".lib.templatetools"
            autoload_lib = __import__(filter_package, {}, {}, ['jinja_filters'])
            try:
                autoload_filters = dict(
                    map(lambda x: (x, autoload_lib.jinja_filters.__dict__[x]),
                                  autoload_lib.jinja_filters.__all__)
                )
            except AttributeError: #pragma: no cover
                autoload_filters = dict(
                    filter(lambda x: callable(x[1]),
                        autoload_lib.jinja_filters.__dict__.iteritems())
                )
        except (ImportError, AttributeError):
            autoload_filters = {}

        # Add jinja filters
        filters = dict(FILTERS, **autoload_filters)
        filters.update(config.jinja_filters)
        jinja2_env.filters = filters

        # Jinja's unable to request c's attributes without strict_c
        config['tg.strict_tmpl_context'] = True

        # Add gettext functions to the jinja environment
        jinja2_env.install_gettext_callables(ugettext, ungettext)

        return {'jinja': cls(jinja2_env)}

    def __init__(self, jinja2_env):
        self.jinja2_env = jinja2_env

    def __call__(self, template_name, template_vars, cache_key=None,
                 cache_type=None, cache_expire=None):
        """Render a template with Jinja2

        Accepts the cache options ``cache_key``, ``cache_type``, and
        ``cache_expire``.

        """
        # Create a render callable for the cache function
        def render_template():
            # Grab a template reference
            template = self.jinja2_env.get_template(template_name)
            return Markup(template.render(**template_vars))

        return cached_template(template_name, render_template,
                               cache_key=cache_key,
                               cache_type=cache_type,
                               cache_expire=cache_expire)


class DottedTemplateLoader(FileSystemLoader):
    """Jinja template loader supporting dotted filenames. Based on Genshi Loader

    """
    def __init__(self, *args, **kwargs):
        self.template_extension = kwargs.pop('template_extension', '.jinja')
        self.dotted_finder = kwargs.pop('dotted_finder')

        super(DottedTemplateLoader, self).__init__(*args, **kwargs)

    def get_source(self, environment, template):
        # Check if dottedname
        if not template.endswith(self.template_extension):
            # Get the actual filename from dotted finder
            finder = self.dotted_finder
            template = finder.get_dotted_filename(template_name=template,
                                                  template_extension=self.template_extension)
        else:
            return FileSystemLoader.get_source(self, environment, template)

        # Check if the template exists
        if not exists(template):
            raise TemplateNotFound(template)

        # Get modification time
        mtime = getmtime(template)

        # Read the source
        fd = open(template, 'rb')
        try:
            source = fd.read().decode('utf-8')
        finally:
            fd.close()

        return source, template, lambda: mtime == getmtime(template)
