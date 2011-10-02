import logging

from gettext import translation

from babel import parse_locale

import formencode

import pylons
import pylons.i18n
from pylons.i18n import add_fallback, LanguageError, get_lang
from pylons.i18n import ugettext, ungettext, lazy_ugettext, gettext_noop
from pylons.configuration import config
from pylons import session

log = logging.getLogger(__name__)


def sanitize_language_code(lang):
    """Sanitize the language code if the spelling is slightly wrong.

    For instance, 'pt-br' and 'pt_br' should be interpreted as 'pt_BR'.

    """
    try:
        lang = '_'.join(filter(None, parse_locale(lang)[:2]))
    except ValueError:
        if '-' in lang:
            try:
                lang = '_'.join(filter(None, parse_locale(lang, sep='-')[:2]))
            except ValueError:
                pass
    return lang


def setup_i18n():
    """Set languages from the request header and the session.

    The session language(s) take priority over the request languages.

    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.

    """
    session_ = pylons.session._current_obj()
    if session_:
        session_existed = session_.accessed()
        # If session is available, we try to see if there are languages set
        languages = session_.get(config.get('lang_session_key', 'tg_lang'))
        if not session_existed and config.get('beaker.session.tg_avoid_touch'):
            session_.__dict__['_sess'] = None

        if languages:
            if isinstance(languages, basestring):
                languages = [languages]
        else:
            languages = []
    else:
        languages = []
    languages.extend(map(sanitize_language_code,
        pylons.request.accept_language.best_matches()))
    set_temporary_lang(languages)


def set_temporary_lang(languages):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.

    try:
        pylons.i18n.set_lang(languages)
    except LanguageError:
        pass
        #log.warn("Language %s: not supported", languages)
    try:
        set_formencode_translation(languages)
    except LanguageError:
        pass
        #log.warn("Language %s: not supported by FormEncode", languages)


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


_localdir = formencode.api.get_localedir()

def set_formencode_translation(languages):
    """Set request specific translation of FormEncode."""
    try:
        formencode_translation = translation(
            'FormEncode',languages=languages, localedir=_localdir)
    except IOError, error:
        raise LanguageError('IOError: %s' % error)
    pylons.tmpl_context.formencode_translation = formencode_translation


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext"
]
