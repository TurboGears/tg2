try:
    from tw2.core import ValidationError as _Tw2ValidationError
except ImportError: #pragma: no cover
    class _Tw2ValidationError(Exception):
        """ToscaWidgets2 Validation Error"""

try:
    from formencode.api import Invalid as _FormEncodeValidationError
    from formencode.api import Validator as _FormEncodeValidator
    from formencode import Schema as _FormEncodeSchema
except ImportError: #pragma: no cover
    class _FormEncodeValidationError(Exception):
        """FormEncode Invalid"""
    class _FormEncodeValidator(object):
        """FormEncode Validator"""
    class _FormEncodeSchema(object):
        """FormEncode Schema"""

def _navigate_tw2form_children(w):
    if getattr(w, 'compound_key', None):
        # If we have a compound_key it's a leaf widget with form values
        yield w
    else:
        child = getattr(w, 'child', None)
        if child:
            # Widgets with "child" don't have children, but their child has
            w = child

        for c in getattr(w, 'children', []):
            for cc in _navigate_tw2form_children(c):
                yield cc

class TGValidationError(Exception):
    """Invalid data was encountered during validation.

    The constructor can be passed a short message with
    the reason of the failed validation.
    """
    def __init__(self, msg, value=None, error_dict=None):
        super(TGValidationError, self).__init__(msg)
        self.msg = msg
        self.value = value
        self.error_dict = error_dict

    @classmethod
    def make_compound_message(cls, error_dict):
        return '\n'.join("%s: %s" % errorinfo for errorinfo in error_dict.items())

    def __str__(self):
        return self.msg

validation_errors = (_Tw2ValidationError, _FormEncodeValidationError, TGValidationError)
