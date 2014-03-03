
class RendererFactory(object):
    """
    Factory that creates one or multiple rendering engines
    for TurboGears. Subclasses have to be registered with
    :func:`tg.configuration.AppConfig.register_rendering_engine`
    and must implement the ``create`` method accordingly.

    """

    #: Here specify the list of engines for which this factory
    #: will create a rendering engine and their options.
    #: They must be specified like::
    #:
    #:   engines = {'json': {'content_type': 'application/json'}}
    #:
    #: Currently only supported option is ``content_type``.
    options = {}

    #: Here specify if turbogears variables have to be injected
    #: in the template context before using any of the declared engines.
    #: Usually ``True`` unless engines are protocols (ie JSON).
    with_tg_vars = True

    @classmethod
    def create(cls, config, app_globals):  # pragma: no cover
        """
        Given the TurboGears configuration and application globals
        it must create a rendering engine for each one specified
        into the ``engines`` list.

        It must return a dictionary in the form::

            {'engine_name': rendering_engine_callable,
             'other_engine': other_rendering_callable}

        Rendering engine callables are callables in the form::

            func(template_name, template_vars,
                 cache_key=None, cache_type=None, cache_expire=None,
                 **render_params)

        ``render_params`` parameter will contain all the values
        provide through ``@expose(render_params={})``.

        """
        raise NotImplementedError()