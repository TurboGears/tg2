import logging

from gettext import translation

from babel import parse_locale

import formencode

import pylons
from pylons.i18n import add_fallback, LanguageError, get_lang 
from pylons.i18n.translation import _get_translator as pylons_get_translator
from pylons.i18n import ugettext, ungettext, lazy_ugettext
from pylons.configuration import config
import tg

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
    if tg.session:
        # If session is available, we try to see if there are languages set
        languages = tg.session.get(
            tg.config.get('lang_session_key', 'tg_lang'))
        if languages:
            if isinstance(languages, basestring):
                languages = [languages]
        else:
            languages = []
    else:
        languages = []
    languages.extend(map(sanitize_language_code,
        tg.request.accept_language.best_matches()))
    set_temporary_lang(languages)

def set_pylons_lang(lang, **kwargs):
    """took from pylons. 
    Sets the current language used for translations by pylons.

    ``lang`` should be a string or a list of strings. If a list of
    strings, the first language is set as the main and the subsequent
    languages are added as fallbacks.
    """
    translator = pylons_get_translator(lang, **kwargs)
    environ = tg.request.environ
    environ['pylons.pylons'].translator = translator
    if 'paste.registry' in environ:
        environ['paste.registry'].replace(pylons.translator, translator)

def set_temporary_lang(languages):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.

    try:
        set_pylons_lang(languages)
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

    if tg.session:
        tg.session[tg.config.get('lang_session_key', 'tg_lang')] = languages
        tg.session.save()


_localdir = formencode.api.get_localedir()

def set_formencode_translation(languages):
    """Set request specific translation of FormEncode."""
    try:
        formencode_translation = translation(
            'FormEncode',languages=languages, localedir=_localdir)
    except IOError, error:
        raise LanguageError('IOError: %s' % error)
    tg.tmpl_context.formencode_translation = formencode_translation


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext"
]
