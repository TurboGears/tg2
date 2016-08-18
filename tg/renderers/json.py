import tg
from tg.jsonify import encode, JSONEncoder
from .base import RendererFactory
from tg.exceptions import HTTPBadRequest

__all__ = ['JSONRenderer']


class JSONRenderer(RendererFactory):
    """
    JSON rendering can be configured using options supported by :meth:`.JSONEncoder.configure`

    Supported ``render_params``:

    - All supported by :meth:`.JSONEncoder.configure`
    - ``key`` -> Render a single key of the dictionary returned by controller
      instead of rendering the dictionary itself.
    - ``callback_param`` ->  Name of the callback to call in rendered JS for **jsonp**

    """
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
    def render_json(template_name, template_vars, **render_params):
        key = render_params.pop('key', None)
        if key is not None:
            template_vars = template_vars[key]

        encode = JSONRenderer._get_configured_encode(render_params)
        return encode(template_vars)

    @staticmethod
    def render_jsonp(template_name, template_vars, **render_params):
        key = render_params.pop('key', None)
        if key is not None:
            template_vars = template_vars[key]

        pname = render_params.pop('callback_param', 'callback')
        callback = tg.request.GET.get(pname)
        if callback is None:
            raise HTTPBadRequest('JSONP requires a "%s" parameter with callback name' % pname)

        encode = JSONRenderer._get_configured_encode(render_params)
        values = encode(template_vars)
        return '%s(%s);' % (callback, values)