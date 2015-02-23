import copy
import logging, os
import gettext as _gettext
from gettext import NullTranslations, GNUTranslations
import warnings
import tg
from tg.util import lazify
from tg._compat import PY3, string_type

log = logging.getLogger(__name__)


class LanguageError(Exception):
    """Exception raised when a problem occurs with changing languages"""
    pass


def _parse_locale(identifier, sep='_'):
    """
    Took from Babel,
    Parse a locale identifier into a tuple of the form::

      ``(language, territory, script, variant)``

    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)

    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:

    :see: `IETF RFC 4646 <http://www.ietf.org/rfc/rfc4646.txt>`_
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or\
           len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant


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
    if PY3: #pragma: no cover
        return tg.translator.gettext(value)
    else:
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
    if PY3: #pragma: no cover
        return tg.translator.ngettext(singular, plural, n)
    else:
        return tg.translator.ungettext(singular, plural, n)
lazy_ungettext = lazify(ungettext)


_TRANSLATORS_CACHE = {}
def _translator_from_mofiles(domain, mofiles, class_=None, fallback=False):
    """
    Adapted from python translation function in gettext module
    to work with a provided list of mo files
    """
    if class_ is None:
        class_ = GNUTranslations

    if not mofiles:
        if fallback:
            return NullTranslations()
        raise LanguageError('No translation file found for domain %s' % domain)

    result = None
    for mofile in mofiles:
        key = (class_, os.path.abspath(mofile))
        t = _TRANSLATORS_CACHE.get(key)
        if t is None:
            with open(mofile, 'rb') as fp:
                # Cache Translator to avoid reading it again
                t = _TRANSLATORS_CACHE.setdefault(key, class_(fp))

        t = copy.copy(t)
        if result is None:
            # Copy the translation object to be able to append fallbacks
            # without affecting the cached object.
            result = t
        else:
            result.add_fallback(t)

    return result


def _get_translator(lang, tgl=None, tg_config=None, **kwargs):
    """Utility method to get a valid translator object from a language name"""
    if tg_config:
        conf = tg_config
    else:
        if tgl:
            conf = tgl.config
        else:  # pragma: no cover
            #backward compatibility with explicit calls without
            #specifying local context or config.
            conf = tg.config.current_conf()

    if not lang:
        return NullTranslations()

    try:
        localedir = conf['localedir']
    except KeyError:  # pragma: no cover
        localedir = os.path.join(conf['paths']['root'], 'i18n')
    app_domain = conf['package'].__name__

    if not isinstance(lang, list):
        lang = [lang]

    mofiles = []
    supported_languages = []
    for l in lang:
        mo = _gettext.find(app_domain, localedir=localedir, languages=[l], all=False)
        if mo is not None:
            mofiles.append(mo)
            supported_languages.append(l)

    try:
        translator = _translator_from_mofiles(app_domain, mofiles, **kwargs)
    except IOError as ioe:
        raise LanguageError('IOError: %s' % ioe)

    translator.tg_lang = lang
    translator.tg_supported_lang = supported_languages

    return translator


def get_lang(all=True):
    """
    Return the current i18n languages used

    returns ``None`` if no supported language is available (no translations
    are in place) or a list of languages.

    In case ``all`` parameter is ``False`` only the languages for which
    the application is providing a translation are returned. Otherwise
    all the languages preferred by the user are returned.
    """
    if all is False:
        return getattr(tg.translator, 'tg_supported_lang', [])
    return getattr(tg.translator, 'tg_lang', [])


def add_fallback(lang, **kwargs):
    """Add a fallback language from which words not matched in other
    languages will be translated to.

    This fallback will be associated with the currently selected
    language -- that is, resetting the language via set_lang() resets
    the current fallbacks.

    This function can be called multiple times to add multiple
    fallbacks.
    """
    tgl = tg.request_local.context._current_obj()
    return tg.translator.add_fallback(_get_translator(lang, tgl=tgl, **kwargs))


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
            lang = '_'.join(filter(None, _parse_locale(lang)[:2]))
        except ValueError:
            if '-' in lang:
                try:
                    lang = '_'.join(filter(None, _parse_locale(lang, sep='-')[:2]))
                except ValueError:
                    pass

        sanitized_language_cache[orig_lang] = lang

    return lang


def set_request_lang(languages, tgl=None):
    """Set the current request language(s) used for translations
    without touching the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    # Should only raise exceptions in case of IO errors,
    # so we let them propagate to the developer.
    tgl.translator = _get_translator(languages, tgl=tgl, fallback=True)

    # If the application has a set of supported translation
    # limit the formencode translations to those so that
    # we don't get the application in a language and
    # the errors in another one
    supported_languages = get_lang(all=False)
    if supported_languages:
        languages = supported_languages

    try:
        set_formencode_translation(languages, tgl=tgl)
    except LanguageError:
        pass


def set_temporary_lang(*args, **kwargs):
    warnings.warn("i18n.set_temporary_lang has been deprecated in favor of"
                  "i18n.set_request_lang and will be removed.", DeprecationWarning)
    return set_request_lang(*args, **kwargs)


def set_lang(languages, **kwargs):
    """Set the current language(s) used for translations
    in current call and session.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    tgl = tg.request_local.context._current_obj()

    set_request_lang(languages, tgl)

    if tgl.session:
        tgl.session[tgl.config.get('lang_session_key', 'tg_lang')] = languages
        tgl.session.save()

FormEncodeMissing = '_MISSING_FORMENCODE'
formencode = None
_localdir = None

def set_formencode_translation(languages, tgl=None):
    """Set request specific translation of FormEncode."""
    global formencode, _localdir
    if formencode is FormEncodeMissing:  # pragma: no cover
        return

    if formencode is None:
        try:
            import formencode
            _localdir = formencode.api.get_localedir()
        except ImportError:  # pragma: no cover
            formencode = FormEncodeMissing
            return

    if not tgl:  # pragma: no cover
        tgl = tg.request_local.context._current_obj()

    try:
        formencode_translation = _gettext.translation('FormEncode',
                                                      languages=languages,
                                                      localedir=_localdir)
    except IOError as error:
        raise LanguageError('IOError: %s' % error)
    tgl.translator._formencode_translation = formencode_translation


# Idea stolen from Pylons
def _formencode_gettext(value):
    trans = ugettext(value)
    # Translation failed, try formencode
    if trans == value:
        try:
            fetrans = tg.translator._formencode_translation
        except (AttributeError, TypeError):
            # the translator was not set in the TG context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = None

        if not fetrans:
            fetrans = NullTranslations()

        translator_gettext = getattr(fetrans, 'ugettext', fetrans.gettext)
        trans = translator_gettext(value)

    return trans


__all__ = [
    "set_lang", "get_lang", "add_fallback",
    "set_request_lang", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext", "lazy_ungettext"
]

