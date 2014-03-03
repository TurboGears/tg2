from tg.jsonify import encode
from .base import RendererFactory

__all__ = ['JSONRenderer']


class JSONRenderer(RendererFactory):
    engines = ['json']
    with_tg_vars = False

    @classmethod
    def create(cls, config, app_globals):
        return {'json': cls()}

    def __call__(self, template_name, template_vars, **kwargs):
        return encode(template_vars)
