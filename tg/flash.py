import logging
from pylons import request, response

COOKIE_NAME = "tg_flash"

def flash(msg):
    """Sets a message to be displayed on the page. This message will survive a
    redirect."""
    # In case no redirect occurs
    request._tg_flash = msg
    response.set_cookie(COOKIE_NAME, msg)

def get_flash():
    """Returns the message previously set by calling flash()"""
    try:
        msg = request._tg_flash
    except AttributeError:
        msg = request.cookies.get(COOKIE_NAME, '')
    response.delete_cookie(COOKIE_NAME)
    return msg
