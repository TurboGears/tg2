import tg
from tg.support.converters import asbool
from tg.configuration.utils import coerce_config
from tg.jsonify import encode, JSONEncoder, _default_encoder
from .base import RendererFactory
from tg.exceptions import HTTPBadRequest

__all__ = ['JSONRenderer']


class JSONRenderer(RendererFactory):
    engines = {'json': {'content_type': 'application/json'},
               'jsonp': {'content_type': 'application/javascript'}}
    with_tg_vars = False

    @classmethod
    def create(cls, config, app_globals):
        return {'json': cls.render_json,
                'jsonp': cls.render_jsonp}

    @staticmethod
    def _get_configured_encode(options):
        # Caching is not supported by JSON encoders
        options.pop('cache_expire', None)
        options.pop('cache_type', None)
        options.pop('cache_key', None)

        if not options:
            return encode
        else:
            return lambda obj: encode(obj, JSONEncoder(**options))

    @staticmethod
    def render_json(template_name, template_vars, **kwargs):
        encode = JSONRenderer._get_configured_encode(kwargs)
        return encode(template_vars)

    @staticmethod
    def render_jsonp(template_name, template_vars, **kwargs):
        pname = kwargs.pop('callback_param', 'callback')
        callback = tg.request.GET.get(pname)
        if callback is None:
            raise HTTPBadRequest('JSONP requires a "%s" parameter with callback name' % pname)

        encode = JSONRenderer._get_configured_encode(kwargs)
        values = encode(template_vars)
        return '%s(%s);' % (callback, values)