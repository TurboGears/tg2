from pyamf.remoting.gateway.wsgi import WSGIGateway
from tg import request

def render_amf(template_name, template_vars, **kwargs):
    assert 0
    # somehow we need to dummy out the services here, but im not sure how
    # yet
    def dummy(*args, **kw):
        return template_vars
    services = {
        'something.method': dummy,
    }

    # setup our server
    app = WSGIGateway(services)
    def start_request(*args, **kw):pass
    r = app(request.environ, start_request)
    return r
