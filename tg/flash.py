import logging
from pylons import request, response

COOKIE_NAME = "tg_flash"
STATUS_NAME = 'tg_status'

def flash(msg, status=None):
    """Sets a message to be displayed on the page. This message will survive a
    redirect.
    
    flash allow to pass in any status, but TurboGears 2 build in three predefined status:
    
      - status_ok
      - status_warning
      - status_alert

    default status: status_ok
    """
    if isinstance(msg, unicode):
        msg = msg.encode('utf8')
    # In case no redirect occurs
    request._tg_flash = msg
    if status:
        request._tg_status = status
        response.set_cookie(STATUS_NAME, request._tg_status)
    response.set_cookie(COOKIE_NAME, msg)

def get_flash():
    """Returns the message previously set by calling flash()"""
    try:
        msg = request._tg_flash
    except AttributeError:
        msg = request.cookies.get(COOKIE_NAME, '')
    response.delete_cookie(COOKIE_NAME)
    return msg.decode('utf8')

def get_status():
    try:
       status = request._tg_status
    except AttributeError:
       status = request.cookies.get(STATUS_NAME, 'status_ok')
    response.delete_cookie(STATUS_NAME)
    return status
