from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 5
_modified_time = 1239703766.6162081
_template_filename='tg/test_stack/rendering/templates/mako_base.mak'
_template_uri='/mako_base.mak'
_template_cache=cache.Cache(__name__, _modified_time)
_source_encoding='utf-8'
from webhelpers.html import escape
_exports = []


def render_body(context,**pageargs):
    context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        self = context.get('self', UNDEFINED)
        __M_writer = context.writer()
        # SOURCE LINE 2
        __M_writer(u'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html>\n  <head>\n    ')
        # SOURCE LINE 6
        __M_writer(escape(self.head_tags()))
        __M_writer(u'\n  </head>\n  <body>\n  \t<p>Inside parent template</p>\n    ')
        # SOURCE LINE 10
        __M_writer(escape(self.body()))
        __M_writer(u'\n  </body>\n</html>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


