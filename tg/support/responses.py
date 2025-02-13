import re

from webob.exc import status_map

from ..exceptions import HTTPFound
from ..jsonify import encode as json_encode
from ..request_local import Response
from ..request_local import request as tg_request
from ..request_local import response as tg_response
from ..support.url import url


def redirect(base_url="/", params=None, redirect_with=HTTPFound, scheme=None):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    if params is None:
        params = {}

    new_url = url(base_url, params=params, scheme=scheme)
    raise redirect_with(location=new_url)


IF_NONE_MATCH = re.compile(r'(?:W/)?(?:"([^"]*)",?\s*)')


def etag_cache(key=None):
    """Use the HTTP Entity Tag cache for Browser side caching

    If a "If-None-Match" header is found, and equivilant to ``key``,
    then a ``304`` HTTP message will be returned with the ETag to tell
    the browser that it should use its current cache of the page.

    Otherwise, the ETag header will be added to the response headers.
    """
    if_none_matches = IF_NONE_MATCH.findall(
        tg_request.environ.get("HTTP_IF_NONE_MATCH", "")
    )
    response = tg_response._current_obj()
    response.etag = key
    if str(key) in if_none_matches:
        response.headers.pop("Content-Type", None)
        response.headers.pop("Cache-Control", None)
        response.headers.pop("Pragma", None)
        raise status_map[304]()


def abort(
    status_code=None,
    detail="",
    headers=None,
    comment=None,
    passthrough=False,
    error_handler=False,
):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    **passthrough**
        When ``True`` instead of displaying the custom error
        document for errors or the authentication page for
        failed authorizations the response will just pass
        through as is.

        Set to ``"json"`` to send out the response body in
        JSON format.

    **error_handler**
        When ``True`` instead of immediately abort the request
        it will create a callable that can be used as ``@validate``
        error_handler.

        A common case is ``abort(404, error_handler=True)`` as
        ``error_handler`` for validation that retrieves objects
        from database::

            from formencode.validators import Wrapper

            @validate({'team': Wrapper(to_python=lambda value:
                                        Group.query.find({'group_name': value}).one())},
                      error_handler=abort(404, error_handler=True))
            def view_team(self, team):
                return dict(team=team)

    """
    exc = status_map[status_code](detail=detail, headers=headers, comment=comment)

    if passthrough == "json":
        exc.content_type = "application/json"
        exc.charset = "utf-8"
        exc.body = json_encode(dict(status=status_code, detail=str(exc))).encode(
            "utf-8"
        )

    def _abortion(*args, **kwargs):
        if passthrough:
            tg_request.environ["tg.status_code_redirect"] = False
            tg_request.environ["tg.skip_auth_challenge"] = True
        raise exc

    if error_handler is False:
        return _abortion()
    else:
        return _abortion


def validation_errors_response(*args, **kwargs):
    """Returns a :class:`.Response` object with validation errors.

    The response will be created with a *412 Precondition Failed*
    status code and errors are reported in JSON format as response body.

    Typical usage is as ``error_handler`` for JSON based api::

        @expose('json')
        @validate({'display_name': validators.NotEmpty(),
                   'group_name': validators.NotEmpty()},
                  error_handler=validation_errors_response)
        def post(self, **params):
            group = Group(**params)
            return dict(group=group)

    """
    req = tg_request._current_obj()
    errors = dict(
        (str(key), str(error)) for key, error in req.validation.errors.items()
    )
    values = req.validation.values
    try:
        return Response(status=412, json_body={"errors": errors, "values": values})
    except TypeError:
        # values cannot be encoded to JSON, this might happen after
        # validation passed and validators converted them to complex objects.
        # In this case use request params, instead of controller params.
        return Response(
            status=412, json_body={"errors": errors, "values": req.args_params}
        )
