import logging, os
from gettext import NullTranslations, translation
from babel.core import parse_locale
import formencode
import tg
from tg.util import lazify

log = logging.getLogger(__name__)

class LanguageError(Exception):
    """Exception raised when a problem occurs with changing languages"""
    pass

def gettext_noop(value):
    """Mark a string for translation without translating it. Returns
    value.
    """
    
    return value

def ugettext(value):
    """Mark a string for translation. Returns the localized unicode
    string of value.

    Mark a string to be localized as follows::

        _('This should be in lots of languages')

    """
    return tg.translator.ugettext(value)
lazy_ugettext = lazify(ugettext)

def ungettext(singular, plural, n):
    """Mark a string for translation. Returns the localized unicode
    string of the pluralized value.

    This does a plural-forms lookup of a message id. ``singular`` is
    used as the message id for purposes of lookup in the catalog, while
    ``n`` is used to determine which plural form to use. The returned
    message is a Unicode string.

    Mark a string to be localized as follows::

        ungettext('There is %(num)d file here', 'There are %(num)d files here',
                  n) % {'num': n}

    """
    return tg.translator.ungettext(singular, plural, n)
lazy_ungettext = lazify(ungettext)


def _get_translator(lang, tgl=None, tg_config=None, **kwargs):
    """Utility method to get a valid translator object from a language
    name"""
    if not lang:
        return NullTranslations()

    if tg_config:
        conf = tg_config
    else:
        if tgl:
            conf = tgl.config
        else:
            conf = tg.config.current_conf()

    try:
        localedir = conf['localedir']
    except KeyError:
        localedir = os.path.join(conf['paths']['root'], 'i18n')

    if not isinstance(lang, list):
        lang = [lang]

    try:
        translator = translation(conf['package'].__name__, localedir, languages=lang, **kwargs)
    except IOError, ioe:
        raise LanguageError('IOError: %s' % ioe)

    translator.tg_lang = lang
    
    return translator


def get_lang():
    """Return the current i18n language used"""
    return getattr(tg.translator, 'tg_lang', None)


def add_fallback(lang, **kwargs):
    """Add a fallback language from which words not matched in other
    languages will be translated to.

    This fallback will be associated with the currently selected
    language -- that is, resetting the language via set_lang() resets
    the current fallbacks.

    This function can be called multiple times to add multiple
    fallbacks.
    """
    return tg.translator.add_fallback(_get_translator(lang, **kwargs))

sanitized_language_cache = {}
def sanitize_language_code(lang):
    """Sanitize the language code if the spelling is slightly wrong.

    For instance, 'pt-br' and 'pt_br' should be interpreted as 'pt_BR'.

    """
    try:
        lang = sanitized_language_cache[lang]
    except:
        orig_lang = lang

        try:
            lang = '_'.join(filter(None, parse_locale(lang)[:2]))
        except ValueError:
            if '-' in lang:
                try:
                    lang = '_'.join(filter(None, parse_locale(lang, sep='-')[:2]))
                except ValueError:
                    pass

        sanitized_language_cache[orig_lang] = lang

    return lang


def setup_i18n(tgl=None):
    """Set languages from the request header and the session.

    The session language(s) take priority over the request languages.

    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.

    """
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    session_ = tgl.session
    if session_:
        session_existed = session_.accessed()
        # If session is available, we try to see if there are languages set
        languages = session_.get(tgl.config.get('lang_session_key', 'tg_lang'))
        if not session_existed and tgl.config.get('beaker.session.tg_avoid_touch'):
            session_.__dict__['_sess'] = None

        if languages:
            if isinstance(languages, basestring):
                languages = [languages]
        else:
            languages = []
    else:
        languages = []
    languages.extend(map(sanitize_language_code, tgl.request.plain_languages))
    set_temporary_lang(languages, tgl=tgl)


def set_temporary_lang(languages, tgl=None):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    try:
        translator = _get_translator(languages, tgl=tgl)
        environ = tgl.request.environ
        tgl.translator = translator
        try:
            tgl.translator = translator
        except KeyError:
            pass
    except LanguageError:
        pass

    try:
        set_formencode_translation(languages, tgl=tgl)
    except LanguageError:
        pass

def set_lang(languages, **kwargs):
    """Set the current language(s) used for translations
    in current call and session.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    tgl = tg.request_local.context._current_obj()

    set_temporary_lang(languages, tgl)

    if tgl.session:
        tgl.session[tgl.config.get('lang_session_key', 'tg_lang')] = languages
        tgl.session.save()


_localdir = formencode.api.get_localedir()

def set_formencode_translation(languages, tgl=None):
    """Set request specific translation of FormEncode."""
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    try:
        formencode_translation = translation(
            'FormEncode',languages=languages, localedir=_localdir)
    except IOError, error:
        raise LanguageError('IOError: %s' % error)
    tgl.tmpl_context.formencode_translation = formencode_translation


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext"
]

