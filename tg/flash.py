import logging
from pylons import request, response, session

def flash(msg, status=None):
    """Sets a message to be displayed on the page. This message will survive a
    redirect.
    
    flash allow to pass in any status, but TurboGears 2 build in three predefined status:
    
      - status_ok
      - status_warning
      - status_alert

    default status: status_ok
    """
    session['flash_message'] = msg
    session['flash_status'] = status or "status_ok"


def get_flash():
    """Returns the message previously set by calling flash()"""
    msg = session.get('flash_message', '')
    return 

def get_status():
    status = session.get('flash_status', 'status_ok')
    return status