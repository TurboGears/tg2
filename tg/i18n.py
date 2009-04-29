import logging

import formencode
import pylons
import pylons.i18n
from pylons.i18n import add_fallback, LanguageError, get_lang
from pylons import config, session

log = logging.getLogger(__name__)

def setup_i18n():
    """Checks to see if there is a lang in session.
    If not, tries to guess best match and applies it.
    
    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.
    """
    languages = pylons.request.accept_language.best_matches()
    
    use_session_lang = False
    
    if pylons.session:
        # If session is available, we try to see if there is a lang set
        lang_session_key = config.get('lang_session_key', 'tg_lang')
        
        if lang_session_key in pylons.session:
            log.info("Language %s found in session",
                         pylons.session[lang_session_key])
            
            try:
                pylons.i18n.set_lang(pylons.session[lang_session_key])
            except LanguageError:
                log.info("Language %s: not supported",
                         pylons.session[lang_session_key])
            else:
                # if there is a resource bundle for this language
                # stop the best match search
                use_session_lang = True
                log.info("Set request language to %s",
                         pylons.session[lang_session_key])
        

    if languages:
        # get a copy of the languages list because we will
        # edit languages and cannot iter directly on it.
        for lang in languages[:]:
            try:
                add_fallback(lang)
            except LanguageError:
                # if there is no resource bundle for this language
                # remove the language from the list
                languages.remove(lang)
                log.info("Skip language %s: not supported", lang)

        # if any language is left, set the best match as a default
        # TODO : Move it upper or add the fallbacks again after,
        # since set_lang resets all the fallbacks.
        if languages and not use_session_lang:
            set_temporary_lang(languages)
                
def set_temporary_lang(languages):
    """Set the current language used for translations without touching
    session language.
    
    languages should be a list.
    First lang will be used as main lang, others as fallbacks
    """
    try:
        pylons.i18n.set_lang(languages)
    except LanguageError:
        log.info("Language %s: not supported", languages[0])
    else:
        log.info("Set request language to %s", languages[0])

    try:
        set_formencode_translation(languages)
    except LanguageError:
        log.info("Language %s: not supported by FormEncode",
                languages[0])
    else:
        log.info("Set request language for FormEncode to %s",
                languages[0])
    
                
def set_lang(lang, **kwargs):
    """Set the current language used for translations
    in current call and session.
    
    lang should be a string.
    """
    set_temporary_lang([lang, ])
        
    if pylons.session:
        lang_session_key = config.get('lang_session_key', 'tg_lang')
        session[lang_session_key] = lang
        session.save()
        
        
def set_formencode_translation(languages):
    """Set request specific translation of FormEncode
    """
    from gettext import translation
    try:
        t = translation('FormEncode', languages=languages,
                localedir=formencode.api.get_localedir())

    except IOError, ioe:
        raise LanguageError('IOError: %s' % ioe)

    pylons.tmpl_context.formencode_translation = t
    
    
__all__ = [
    "setup_i18n", "set_lang", "get_lang", "set_temporary_lang"
]