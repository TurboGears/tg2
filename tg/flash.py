"""Flash messaging system for sending info to the user in a
non-obtrusive way
"""
from webflash import Flash
from pylons import response, request

from logging import getLogger

log = getLogger(__name__)

class TGFlash(Flash):
    def __call__(self, message, status=None, **extra_payload):
        log.debug("flash: message=%r, status=%s", message, status)
        return super(TGFlash, self).__call__(
            unicode(message), status, request=request, response=response,
            **extra_payload
            )

flash = TGFlash(default_status="ok")

def get_flash():
    """Returns the message previously set by calling flash()
    
    Additonally removes the old flash message """
    return flash.pop_payload(request, response).get('message')

def get_status():
    """Returns the status of the last flash messagese
    
    Additonally removes the old flash message status"""
    return flash.pop_payload(request, response).get('status') or 'ok'
