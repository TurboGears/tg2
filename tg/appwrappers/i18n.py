import logging
from ..i18n import sanitize_language_code, set_request_lang
from .._compat import string_type
from ..support.converters import asbool
from ..configuration.utils import coerce_config
from .base import ApplicationWrapper

log = logging.getLogger(__name__)


class I18NApplicationWrapper(ApplicationWrapper):
    """Provides Language detection from request and session.

    The session language(s) take priority over the request languages.

    Supported options which can be provided by config are:
        - ``i18n.enabled``: Whenever language detection is enabled or not.
        - ``i18n.lang``: Fallback language for the application, works both when language
          detection is enabled or disabled. If this is set and language detection is
          dislabled, the application will consider that all gettext wrapped strings must
          be translated to this language.
        - ``i18n.lang_session_key``: Session key from which to read the saved language
          (``tg_lang`` by default).
        - ``i18n.no_session_touch``: Avoid causing a session save when reading it to retrieve the
          favourite user language. This is ``False`` by default, setting it to ``False`` causes
          TurboGears to save and update the session for each request.

    """
    def __init__(self, handler, config):
        super(I18NApplicationWrapper, self).__init__(handler, config)

        options = {
            'enabled': False,
            'lang_session_key': 'tg_lang',
            'no_session_touch': False,
            'lang': None
        }
        options.update(coerce_config(config, 'i18n.',  {
            'enabled': asbool,
            'no_session_touch': asbool,
        }))

        self.enabled = options['enabled']
        self.options = options
        log.debug('i18n enabled: %s -> %s', self.enabled, self.options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        session_ = context.session
        if session_:
            session_existed = session_.accessed()
            # If session is available, we try to see if there are languages set
            languages = session_.get(self.options['lang_session_key'])
            if not session_existed and self.options['no_session_touch']:
                session_.__dict__['_sess'] = None

            if languages:
                if isinstance(languages, string_type):
                    languages = [languages]
            else:
                languages = []
        else:  # pragma: no cover
            languages = []

        languages.extend(map(sanitize_language_code, context.request.languages))
        set_request_lang(languages, tgl=context)

        return self.next_handler(controller, environ, context)
