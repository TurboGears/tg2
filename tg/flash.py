"""Flash messaging system for sending info to the user in a
non-obtrusive way
"""
from pylons import session

def flash(msg, status=None):
    """Sets a message to be displayed on the page. This message will survive a
    redirect.
    
    flash allows to pass in any status, but TurboGears 2 build in three
    predefined status:
    
      - status_ok
      - status_warning
      - status_alert

    default status: status_ok
    """
    session['flash_message'] = msg
    session['flash_status'] = status or "status_ok"
    session.save()
    
def get_flash():
    """Returns the message previously set by calling flash()
    
    Additonally removes the old flash message """
    msg = session.get('flash_message', '')
    session['flash_message'] = ''
    session.save()
    return msg

def get_status():
    """Returns the status of the last flash messagese
    
    Additonally removes the old flash message status"""
    
    status = session.get('flash_status', 'status_ok')
    session['flash_status'] = ''
    session.save()
    return status
    
