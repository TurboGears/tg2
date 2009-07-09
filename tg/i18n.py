import logging

import formencode
import pylons
import pylons.i18n
from pylons.i18n import add_fallback, LanguageError, get_lang
from pylons import config, session

log = logging.getLogger(__name__)


def setup_i18n():
    """Set languages from the request header and the session.

    The session language(s) take priority over the request languages.

    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.
    """
    if pylons.session:
        # If session is available, we try to see if there are languages set
        languages = pylons.session.get(
            config.get('lang_session_key', 'tg_lang'))
        if languages:
            if isinstance(languages, basestring):
                languages = [languages]
        else:
            languages = []
    else:
        languages = []
    languages.extend(pylons.request.accept_language.best_matches())
    set_temporary_lang(languages)


def set_temporary_lang(languages):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.
    """
    try:
        pylons.i18n.set_lang(languages)
    except LanguageError:
        log.info("Language %s: not supported", languages)
    else:
        log.info("Set request language to %s", languages)
    try:
        set_formencode_translation(languages)
    except LanguageError:
        log.info("Language %s: not supported by FormEncode", languages)
    else:
        log.info("Set request language for FormEncode to %s", languages)


def set_lang(languages, **kwargs):
    """Set the current language(s) used for translations
    in current call and session.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.
    """
    set_temporary_lang(languages)

    if pylons.session:
        session[config.get('lang_session_key', 'tg_lang')] = languages
        session.save()


def set_formencode_translation(languages):
    """Set request specific translation of FormEncode."""
    from gettext import translation
    try:
        formencode_translation = translation('FormEncode',
            languages=languages, localedir=formencode.api.get_localedir())
    except IOError, error:
        raise LanguageError('IOError: %s' % error)
    pylons.tmpl_context.formencode_translation = formencode_translation


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang"
]