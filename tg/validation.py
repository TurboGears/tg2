from tg.configuration.utils import TGConfigError

from .i18n import lazy_ugettext


class _ValidationStatus(object):
    """Current request parameters validation status.

    Keeps track of currently validated values, errors and
    the ValidationIntent that caused the validation process.
    """

    __slots__ = ("errors", "values", "exception", "intent")

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

    @property
    def chain_validation(self):
        if self.intent is None:
            return False
        return self.intent.chain_validation


class _ValidationIntent(object):
    """Details of validation intention.

    Describes how a validation should happen and how
    errors should be handled. It also performs the
    validation itself on the parameters for a given
    controller method.
    """

    def __init__(self, validators, error_handler, chain_validation):
        self.validators = validators
        self.error_handler = error_handler
        self.chain_validation = chain_validation

    def check(self, config, method, params):
        validators = self.validators
        if not validators:
            return params

        validation_exceptions = tuple(config["validation.exceptions"])
        validation_validators = config["validation.validators"]
        validated_params = {}

        # The validator may be a dictionary, on of the registered validators or
        # any object with a "validate" method.
        if isinstance(validators, dict):
            # TG developers can pass in a dict of param names and validators.
            # They are applied one by one and builds up a new set
            # of validated params.

            errors = {}
            for field, validator in validators.items():
                try:
                    validated_params[field] = validator.to_python(params.get(field))
                except validation_exceptions as inv:
                    # catch individual validation errors into the errors dictionary
                    errors[field] = inv

            # Parameters that don't have validators are returned verbatim
            for param, param_value in params.items():
                if param not in validated_params:
                    validated_params[param] = param_value

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise TGValidationError(
                    TGValidationError.make_compound_message(errors),
                    value=params,
                    error_dict=errors,
                )
        elif hasattr(validators, "validate") and getattr(
            self, "needs_controller", False
        ):
            # An object with a "validate" method - call it with the parameters
            validated_params = validators.validate(method, params)
        elif hasattr(validators, "validate"):
            # An object with a "validate" method - call it with the parameters
            validated_params = validators.validate(params)
        else:
            schema_class = validators.__class__
            validation_function = None
            for supported_class in validation_validators:
                if issubclass(schema_class, supported_class):
                    validation_function = validation_validators[supported_class]

            if validation_function is None:
                raise TGConfigError(
                    f"No validation validator function found for: {schema_class}"
                )

            validated_params = validation_function(validators, params)

        return validated_params


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
        return str("\n").join(
            str("%s: %s") % errorinfo for errorinfo in error_dict.items()
        )

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
            'num': Convert(int, 'Must be a number')
        }, error_handler=insert_number)
        def post_pow2(self, num):
            return str(num*num)
    """

    def __init__(self, func, msg=lazy_ugettext("Invalid"), default=None):
        self._func = func
        self._msg = msg
        self._default = default

    def to_python(self, value, state=None):
        if RequireValue.is_empty(value):
            if self._default is None:
                raise TGValidationError(self._msg, value)
            return self._default

        try:
            return self._func(value)
        except Exception:
            raise TGValidationError(self._msg, value)


class RequireValue(object):
    """Mark a value as required during validation.

    This is meant to be used when a value is required,
    but not conversion needs to happen.
    This is usually common for string values.

    In case conversion has to happen, use :class:`Convert`
    which will already fail if no value is provided.

    Example::

        @expose()
        @validate({
            'num': RequireValue('you must provide a number')
        }, error_handler=insert_number)
        def post_pow2(self, num):
            return str(num*num)
    """

    def __init__(self, msg=lazy_ugettext("Required")):
        self._msg = msg

    @staticmethod
    def is_empty(value):
        return value in (None, "", b"", [], {}, tuple())

    def to_python(self, value, state=None):
        if self.is_empty(value):
            raise TGValidationError(self._msg, value)
        return value
