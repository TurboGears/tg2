import warnings
from .i18n import _formencode_gettext, lazy_ugettext

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


class _ValidationStatus(object):
    """Current request parameters validation status.

    Keeps track of currently validated values, errors and
    the ValidationIntent that caused the validation process.
    """
    __slots__ = ('errors', 'values', 'exception', 'intent')

    def __init__(self, errors=None, values=None, exception=None, intent=None):
        self.errors = errors or {}
        self.values = values or {}
        self.exception = exception
        self.intent = intent

    @property
    def error_handler(self):
        if self.intent is None:
            return None

        return self.intent.error_handler

    def __getitem__(self, item):
        warnings.warn("Accessing validation status properties with [] syntax is deprecated. "
                      " Please use dot notation instead", DeprecationWarning)
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError


class _ValidationIntent(object):
    """Details of validation intention.

    Describes how a validation should happen and how
    errors should be handled. It also performs the
    validation itself on the parameters for a given
    controller method.
    """
    def __init__(self, validators, error_handler):
        self.validators = validators
        self.error_handler = error_handler

    def check(self, method, params):
        validators = self.validators
        if not validators:
            return params

        # An object used by FormEncode to get translator function
        formencode_state = type('state', (), {'_': staticmethod(_formencode_gettext)})
        validated_params = {}

        # The validator may be a dictionary, a FormEncode Schema object, or any
        # object with a "validate" method.
        if isinstance(validators, dict):
            # TG developers can pass in a dict of param names and FormEncode
            # validators.  They are applied one by one and builds up a new set
            # of validated params.

            errors = {}
            for field, validator in validators.items():
                try:
                    if isinstance(validator, _FormEncodeValidator):
                        validated_params[field] = validator.to_python(params.get(field), formencode_state)
                    else:
                        validated_params[field] = validator.to_python(params.get(field))
                # catch individual validation errors into the errors dictionary
                except validation_errors as inv:
                    errors[field] = inv

            # Parameters that don't have validators are returned verbatim
            for param, param_value in params.items():
                if param not in validated_params:
                    validated_params[param] = param_value

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise TGValidationError(TGValidationError.make_compound_message(errors),
                                        value=params,
                                        error_dict=errors)

        elif isinstance(validators, _FormEncodeSchema):
            # A FormEncode Schema object - to_python converts the incoming
            # parameters to sanitized Python values
            validated_params = validators.to_python(params, formencode_state)

        elif hasattr(validators, 'validate') and getattr(self, 'needs_controller', False):
            # An object with a "validate" method - call it with the parameters
            validated_params = validators.validate(method, params, formencode_state)

        elif hasattr(validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            validated_params = validators.validate(params, formencode_state)

        return validated_params


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
        return str(self.msg)


class Convert(object):
    """Applies a conversion function as a validator.

    This is meant to implement simple validation mechanism.

    Any callable can be used for ``func`` as far as it accepts an argument and
    returns the converted object. In case of exceptions the validation
    is considered failed and the ``msg`` parameter is displayed as
    an error.

    A ``default`` value can be provided for values that are missing
    (evaluate to false) which will be used in place of the missing value.

    Example::

        @expose()
        @validate({
            'num': Converter(int, 'Must be a number')
        }, error_handler=insert_number)
        def post_pow2(self, num):
            return str(num*num)
    """
    def __init__(self, func, msg=lazy_ugettext('Invalid'), default=None):
        self._func = func
        self._msg = msg
        self._default = default

    def to_python(self, value, state=None):
        value = value or self._default

        try:
            return self._func(value)
        except:
            raise TGValidationError(self._msg, value)


validation_errors = (_Tw2ValidationError, _FormEncodeValidationError, TGValidationError)
