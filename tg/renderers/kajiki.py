from __future__ import absolute_import
import os

from tg.render import cached_template
from markupsafe import Markup
from .base import RendererFactory
from ..configuration.utils import coerce_config
from ..support.converters import asbool, aslist
from ..i18n import ugettext

try:
    import kajiki
except ImportError:  # pragma: no cover
    kajiki = None

if kajiki is not None:
    from kajiki.loader import FileLoader
else:  # pragma: no cover
    class FileLoader(object): pass

__all__ = ['KajikiRenderer']


class KajikiRenderer(RendererFactory):
    """
    Configuration Options available as ``templating.kajiki.*``:

        - ``templating.kajiki.force_mode`` -> Kajiki Rendering Mode (html, html5, xml). Default ``html5``.
        - ``templating.kajiki.template_extension`` -> Kajiki Templates extension, default ``.xhtml``
        - ``templating.kajiki.xml_autoblocks`` -> List of tags that should be automatically converted to blocks.
        - ``templating.kajiki.cdata_scripts`` -> Automatically wrap scripts in CDATA.
        - ``templating.kajiki.html_optional_tags`` -> Allow unclosed html, head and body tags.
        - ``templating.kajiki.strip_text`` -> Strip leading/trailing spaces from text nodes.

    Supported ``render_params``:

        - Caching options supported by :func:`.cached_template`
        - All arguments supported by :func:`kajiki.xml_template.XMLTemplate`

    """
    CONFIG_OPTIONS = {
        'force_mode': str,
        'template_extension': str,
        'autoescape_text': asbool,
        'xml_autoblocks': aslist,
        'cdata_scripts': asbool,
        'html_optional_tags': asbool,
        'strip_text': asbool
    }
    engines = {'kajiki': {'content_type': 'text/html'}}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for the Kajiki engine."""
        if kajiki is None:  # pragma: no cover
            return None

        options = coerce_config(config, 'templating.kajiki.', cls.CONFIG_OPTIONS)
        if not options.get('html_optional_tags', False):
            # Kajiki by default doesn't close BODY and HEAD tags, but this behaviour
            # breaks TW2 resources that get injected at the end of head or body.
            # So by default we force Kajiki to close those tags.
            from kajiki import html_utils
            html_utils.HTML_OPTIONAL_END_TAGS.discard('html')
            html_utils.HTML_OPTIONAL_END_TAGS.discard('head')
            html_utils.HTML_OPTIONAL_END_TAGS.discard('body')

        # This is official way to switch gettext function in kajiki
        # as documented in http://pythonhosted.org/Kajiki/i18n.html
        from kajiki import i18n
        i18n.gettext = ugettext

        loader = KajikiTemplateLoader(config['paths'].templates[0],
                                      dotted_finder=app_globals.dotted_filename_finder,
                                      reload=config['auto_reload_templates'],
                                      **options)
        return {'kajiki': cls(loader)}

    def __init__(self, loader):
        self.loader = loader

    def __call__(self, template_name, template_vars, cache_key=None,
                 cache_type=None, cache_expire=None, **render_params):
        """Render a template with Kajiki

        Accepts the cache options ``cache_key``, ``cache_type``, and
        ``cache_expire``.

        """
        # Create a render callable for the cache function
        def render_template():
            # Grab a template reference
            template = self.loader.load(template_name, **render_params)
            return Markup(template(template_vars).render())

        return cached_template(template_name, render_template,
                               cache_key=cache_key, cache_type=cache_type,
                               cache_expire=cache_expire)


class KajikiTemplateLoader(FileLoader):
    """Kaijik template loader supporting dotted filenames.
    Solves also the issue of not supporting relative paths when using
    py:extends in Kaijiki
    """
    def __init__(self, base, dotted_finder, reload=True, force_mode='html5', **kwargs):
        self.dotted_finder = dotted_finder
        self.template_extension = kwargs.pop('template_extension', '.xhtml')

        super(KajikiTemplateLoader, self).__init__(base, reload, force_mode, **kwargs)

    def _filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = self.dotted_finder
            filename = finder.get_dotted_filename(template_name=filename,
                                                  template_extension=self.template_extension)

            if not os.path.exists(filename):
                raise IOError('Template %s not found' % filename)

        resolved_filename = super(KajikiTemplateLoader, self)._filename(filename)
        if resolved_filename is None:
            raise IOError('Template %s not found in template paths' % filename)
        return resolved_filename
