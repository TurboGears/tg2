
__all__ = ('ValidationConfigurationComponent', )
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction


class ValidationConfigurationComponent(ConfigurationComponent):
    """Provides support for validation.

    The available options are:

        - ``validation.exceptions`` -> ``list`` of exception classes that needs to be considered
           validation errors. ``TGValidationError`` is always included.

    """
    id = 'validation'

    def get_defaults(self):
        return {
            'validation.exceptions': [],
            'validation.explode': {}
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_validation),
            BeforeConfigConfigurationAction(self._configure_explode)
        )

    def _configure_validation(self, conf, app):
        validation_exceptions = conf['validation.exceptions']

        from tg.validation import TGValidationError
        if TGValidationError not in validation_exceptions:
            validation_exceptions.append(TGValidationError)

        try:
            from formencode.api import Invalid as _FormEncodeValidationError
        except ImportError:
            pass
        else:
            if _FormEncodeValidationError not in validation_exceptions:
                validation_exceptions.append(_FormEncodeValidationError)

    def _configure_explode(self, conf, app):
        validation_explode = conf['validation.explode']

        from tg.validation import TGValidationError
        if TGValidationError not in validation_explode:
            validation_explode[TGValidationError] = _explode_tgvalidationerror


def _explode_tgvalidationerror(exception):
    return {'errors': exception.error_dict, 'values': exception.value}