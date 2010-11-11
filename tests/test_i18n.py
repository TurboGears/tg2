# -*- coding: utf-8 -*-

from tg import i18n


def test_sanitize_language_code():
    """Check that slightly malformed language codes can be corrected."""
    for lang in 'pt', 'PT':
        assert i18n.sanitize_language_code(lang) == 'pt'
    for lang in 'pt-br', 'pt_br', 'pt_BR':
        assert i18n.sanitize_language_code(lang) == 'pt_BR'
    for lang in 'foo', 'bar', 'foo-bar':
        assert i18n.sanitize_language_code(lang) == lang
