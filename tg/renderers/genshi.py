from __future__ import absolute_import

from markupsafe import Markup
from tg.support.converters import asint, asbool
from tg.i18n import ugettext
from tg.render import cached_template
from .base import RendererFactory
import tg

try:
    import genshi
except ImportError:  # pragma: no cover
    genshi = None

if genshi is not None:
    from genshi.template import TemplateLoader as GenshiTemplateLoader
    from genshi.filters import Translator
    from genshi import HTML, XML
else:  # pragma: no cover
    class GenshiTemplateLoader(object): pass


__all__ = ['GenshiRenderer']


class GenshiRenderer(RendererFactory):
    """Singleton that can be called as the Genshi render function."""
    engines = {'genshi': {'content_type': 'text/html'}}

    doctypes_for_methods = {
        'html': 'html-transitional',
        'xhtml': 'xhtml-transitional'}

    doctypes_for_content_type = {
        'text/html': ('html', 'html-transitional',
            'html-frameset', 'html5',
            'xhtml', 'xhtml-strict',
            'xhtml-transitional', 'xhtml-frameset'),
        'application/xhtml+xml': ('xhtml', 'xhtml-strict',
            'xhtml-transitional',
            'xhtml-frameset', 'xhtml11'),
        'image/svg+xml': ('svg', 'svg-full', 'svg-basic', 'svg-tiny')}

    methods_for_content_type = {
        'text/plain': ('text',),
        'text/css': ('text',),
        'text/html': ('html', 'xhtml'),
        'text/xml': ('xml', 'xhtml'),
        'application/xml': ('xml', 'xhtml'),
        'application/xhtml+xml': ('xhtml',),
        'application/atom+xml': ('xml',),
        'application/rss+xml': ('xml',),
        'application/soap+xml': ('xml',),
        'image/svg+xml': ('xml',)}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for Genshi templates.

        Override this to customize the way that the internationalization
        filter, template loader

        """
        if genshi is None:  # pragma: no cover
            # Genshi not available
            return None

        # Patch for Genshi on Python3.4
        if asbool(config.get('templating.genshi.name_constant_patch', False)):
            from genshi.template.astutil import ASTCodeGenerator
            if not hasattr(ASTCodeGenerator, 'visit_NameConstant'):
                def _visit_NameConstant(self, node):
                    if node.value is None:
                        self._write('None')
                    elif node.value is True:
                        self._write('True')
                    elif node.value is False:
                        self._write('False')
                    else:
                        raise Exception("Unknown NameConstant %r" % (node.value,))
                ASTCodeGenerator.visit_NameConstant = _visit_NameConstant

        if config.get('use_dotted_templatenames', True):
            TemplateLoader = DottedTemplateLoader
            template_loader_args = {'dotted_finder': app_globals.dotted_filename_finder}
        else:
            TemplateLoader = GenshiTemplateLoader
            template_loader_args = {}

        loader = TemplateLoader(search_path=config.paths.templates,
                                max_cache_size=asint(config.get('genshi.max_cache_size', 30)),
                                auto_reload=config.auto_reload_templates,
                                callback=cls.on_template_loaded,
                                **template_loader_args)

        return {'genshi': cls(loader, config)}

    def __init__(self, loader, config):
        self.tg_config = config
        self.genshi_functions = dict(HTML=HTML, XML=XML)
        self.load_template = loader.load

        self.default_doctype = None
        doctype = self.tg_config.get('templating.genshi.doctype')
        if doctype:
            if isinstance(doctype, str):
                self.default_doctype = doctype
            elif isinstance(doctype, dict):
                doctypes = self.doctypes_for_content_type.copy()
                doctypes.update(doctype)
                self.doctypes_for_content_type = doctypes

        self.default_method = None
        method = self.tg_config.get('templating.genshi.method')
        if method:
            if isinstance(method, str):
                self.default_method = method
            elif isinstance(method, dict):
                methods = self.methods_for_content_type.copy()
                methods.update(method)
                self.methods_for_content_type = methods

    @classmethod
    def on_template_loaded(cls, template):
        """
        Plug-in our i18n function to Genshi, once the template is loaded.

        This function will be called by the Genshi TemplateLoader after
        loading the template.

        """
        translator = Translator(ugettext)
        template.filters.insert(0, translator)

        if hasattr(template, 'add_directives'):
            template.add_directives(Translator.NAMESPACE, translator)

    @staticmethod
    def method_for_doctype(doctype):
        method = 'xhtml'
        if doctype:
            if doctype.startswith('html'):
                method = 'html'
            elif doctype.startswith('xhtml'):
                method = 'xhtml'
            elif doctype.startswith('svg'):
                method = 'xml'
            else:
                method = 'xhtml'
        return method

    def __call__(self, template_name, template_vars, **kwargs):
        """Render the template_vars with the Genshi template.

        If you don't pass a doctype or pass 'auto' as the doctype,
        then the doctype will be automatically determined.
        If you pass a doctype of None, then no doctype will be injected.
        If you don't pass a method or pass 'auto' as the method,
        then the method will be automatically determined.

        """
        response = tg.response._current_obj()

        template_vars.update(self.genshi_functions)

        # Gets document type from content type or from config options
        doctype = kwargs.get('doctype', 'auto')
        if doctype == 'auto':
            doctype = self.default_doctype
            if not doctype:
                method = kwargs.get('method') or self.default_method or 'xhtml'
                doctype = self.doctypes_for_methods.get(method)
            doctypes = self.doctypes_for_content_type.get(response.content_type)
            if doctypes and (not doctype or doctype not in doctypes):
                doctype = doctypes[0]
            kwargs['doctype'] = doctype

        # Gets rendering method from content type or from config options
        method = kwargs.get('method')
        if not method or method == 'auto':
            method = self.default_method
            if not method:
                method = self.method_for_doctype(doctype)
            methods = self.methods_for_content_type.get(response.content_type)
            if methods and (not method or method not in methods):
                method = methods[0]
            kwargs['method'] = method

        def render_template():
            template = self.load_template(template_name)
            return Markup(template.generate(**template_vars).render(
                doctype=doctype,
                method=method,
                encoding=None)
            )

        return cached_template(template_name, render_template,
                               ns_options=('doctype', 'method'), **kwargs)


class DottedTemplateLoader(GenshiTemplateLoader):
    """
    Genshi template loader supporting dotted filenames.
    Supports zipped applications and dotted filenames as well as path names.

    """
    def __init__(self, *args, **kwargs):
        self.template_extension = kwargs.pop('template_extension', '.html')
        self.dotted_finder = kwargs.pop('dotted_finder')

        super(DottedTemplateLoader, self).__init__(*args, **kwargs)

    def get_dotted_filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = self.dotted_finder
            filename = finder.get_dotted_filename(template_name=filename,
                                                  template_extension=self.template_extension)
        return filename

    def load(self, filename, relative_to=None, cls=None, encoding=None):
        """Actual loader function."""
        return super(DottedTemplateLoader, self).load(self.get_dotted_filename(filename),
                                                      relative_to=relative_to, cls=cls,
                                                      encoding=encoding)
