import tg
from tg.jsonify import encode
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
    def render_json(template_name, template_vars, **kwargs):
        return encode(template_vars)

    @staticmethod
    def render_jsonp(template_name, template_vars, **kwargs):
        pname = kwargs.get('callback_param', 'callback')
        callback = tg.request.GET.get(pname)
        if callback is None:
            raise HTTPBadRequest('JSONP requires a "%s" parameter with callback name' % pname)

        values = encode(template_vars)
        return '%s(%s);' % (callback, values)