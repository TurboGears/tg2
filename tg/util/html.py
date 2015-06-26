from ..jsonify import encode as json_encode


def script_json_encode(obj, **kwargs):
    """Works exactly like :func:`tg.jsonify.encode` but is safe
    for use in ``<script>`` tags.

    The following characters are escaped in strings:
        -   ``<``
        -   ``>``
        -   ``&``
        -   ``'``

    This makes it safe to embed such strings in any place in HTML with the
    notable exception of double quoted attributes.  In that case single
    quote your attributes or HTML escape it in addition.
    """
    rv = json_encode(obj, **kwargs) \
        .replace(u'<', u'\\u003c') \
        .replace(u'>', u'\\u003e') \
        .replace(u'&', u'\\u0026') \
        .replace(u"'", u'\\u0027')

    return rv


