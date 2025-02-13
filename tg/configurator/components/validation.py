__all__ = ("ValidationConfigurationComponent",)
from ..base import BeforeConfigConfigurationAction, ConfigurationComponent


class ValidationConfigurationComponent(ConfigurationComponent):
    """Provides support for validation.

    The available options are:

        - ``validation.exceptions`` -> ``list`` of exception classes that needs to be considered
           validation errors. ``TGValidationError`` is always included.
        - ``validation.explode`` -> ``dict`` of exception classes with associated callabe
          ``callable(exc) -> {'errors': {str: str}, 'values': {str: Any}}``. This is used to
          expand validation errors when one occurs.
        - ``validation.validators`` -> ``dict`` of schema classes with associate callables
          ``callable(schema: Any, params: dict) -> {str: Any}`` returning the parameters after
          validation and conversion. In case of validation failure it must raise one of the
          ``validation.exceptions``.

    """

    id = "validation"

    def get_defaults(self):
        return {
            "validation.exceptions": [],
            "validation.explode": {},
            "validation.validators": {},
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_validation),
            BeforeConfigConfigurationAction(self._configure_explode),
        )

    def _configure_validation(self, conf, app):
        validation_exceptions = conf["validation.exceptions"]

        from tg.validation import TGValidationError

        if TGValidationError not in validation_exceptions:
            validation_exceptions.append(TGValidationError)

    def _configure_explode(self, conf, app):
        validation_explode = conf["validation.explode"]

        from tg.validation import TGValidationError

        if TGValidationError not in validation_explode:
            validation_explode[TGValidationError] = _explode_tgvalidationerror


def _explode_tgvalidationerror(exception):
    return {"errors": exception.error_dict, "values": exception.value}
