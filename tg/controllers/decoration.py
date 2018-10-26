# -*- coding: utf-8 -*-
import warnings

from webob.acceptparse import create_accept_header

from tg.configuration import milestones
from tg.configuration import config

import logging
log = logging.getLogger(__name__)


def _decorated_controller_caller(tg_config, controller, remainder, params):
    try:
        application_controller_caller = tg_config['controller_caller']
    except KeyError:  # pragma: no cover
        # This should never happen as controller_caller is setup by MinimalApplicationConfigurator.
        from tg.configurator.components.dispatch import _call_controller
        application_controller_caller = _call_controller

    return application_controller_caller(tg_config, controller, remainder, params)


class Decoration(object):
    """ Simple class to support 'simple registration' type decorators
    """
    def __init__(self, controller):
        self.controller = controller
        self.controller_caller = _decorated_controller_caller
        self._expositions = []
        self.engines = {}
        self.engines_keys = []
        self.default_engine = None
        self.custom_engines = {}
        self.render_custom_format = None
        self.validations = []
        self.inherit = False
        self.requirements = []
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[])

    def __repr__(self): # pragma: no cover
        return '<Decoration %s for %r>' % (id(self), self.controller)

    @classmethod
    def get_decoration(cls, func):
        try:
            dec = func.decoration
        except:
            dec = func.decoration = cls(func)
        return dec

    def _register_exposition(self, exposition, inherit=False, before=False):
        """Register an exposition for later application"""

        # We need to store a reference to the exposition
        # so that we can merge them when inheritance is performed
        if before:
            self._expositions.insert(0, exposition)
        else:
            self._expositions.append(exposition)

        if inherit:
            # if at least one exposition is in inherit mode
            # all of them must inherit
            self.inherit = True

        milestones.renderers_ready.register(self._resolve_expositions)

    def _resolve_expositions(self):
        """Applies all the registered expositions"""
        while True:
            try:
                exposition = self._expositions.pop(0)
                exposition._apply()
            except IndexError:
                break

    @property
    def requirement(self):  # pragma: no cover
        warnings.warn("Decoration.requirement is deprecated, "
                      "please use 'requirements' instead", DeprecationWarning, stacklevel=2)
        try:
            return self.requirements[0]
        except IndexError:
            return None

    @property
    def exposed(self):
        return bool(self.engines) or bool(self.custom_engines)

    @property
    def validation(self):
        warnings.warn("Decoration.validation is deprecated, "
                      "please use 'validations' instead", DeprecationWarning, stacklevel=2)
        try:
            return self.validations[0]
        except IndexError:
            return None

    def merge(self, deco):
        # This merges already registered template engines
        self.engines = dict(tuple(deco.engines.items()) + tuple(self.engines.items()))
        self.engines_keys = sorted(self.engines, reverse=True)
        self.custom_engines = dict(tuple(deco.custom_engines.items()) + tuple(self.custom_engines.items()))

        # This merges yet to register template engines
        for exposition in reversed(deco._expositions):
            self._register_exposition(exposition._clone(self.controller), before=True)

        # inherit all the parent hooks
        # parent hooks before current hooks so that they get called before
        for hook_name, hooks in deco.hooks.items():
            self.hooks[hook_name] = hooks + self.hooks[hook_name]

        # Inherit al validators registered on parent.
        self.validations = deco.validations + self.validations

    def register_template_engine(self,
            content_type, engine, template, exclude_names, render_params):
        """Registers an engine on the controller.

        Multiple engines can be registered, but only one engine per
        content_type.  If no content type is specified the engine is
        registered at */* which is the default, and will be used
        whenever no content type is specified.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """
        default_renderer = config.get('default_renderer')
        available_renderers = config.get('renderers', [])

        if engine and not available_renderers:
            log.warning('Renderers not registered yet while exposing template %s for engine %s, '
                        'skipping engine availability check', template, engine)

        if engine and available_renderers and engine not in available_renderers:
            log.debug('Registering template %s for engine %s not available. Skipping it',
                      template, engine)
            return

        content_type = content_type or '*/*'

        try:
            current_content_type_engine = self.engines[content_type][0]
        except (KeyError, IndexError):
            current_content_type_engine = None

        if current_content_type_engine is not None and engine != default_renderer:
            # Avoid overwriting the default renderer when there is already a template registered
            return

        self.engines[content_type] = (engine, template, exclude_names or [], render_params or {})

        # Avoid engine lookup if we have only one engine registered
        if len(self.engines) == 1:
            self.default_engine = content_type
        else:
            self.default_engine = None

        # This is a hack to make text/html prominent in respect to other common choices
        # when they have the same weight for webob.acceptparse.Accept.best_match().
        # It uses the fact that the most common content types are all alphabetically
        # precedent to text/html, and so sorting engine keys alphabetically reversed
        # should make text/html the first choice when no other better choices are available.
        self.engines_keys = sorted(self.engines, reverse=True)

    def register_custom_template_engine(self, custom_format,
            content_type, engine, template, exclude_names, render_params):
        """Registers a custom engine on the controller.

        Multiple engines can be registered, but only one engine per
        custom_format.

        The engine is registered when @expose is used with the
        custom_format parameter and controllers render using this
        engine when the :meth:`use_custom_format` function is called
        with the corresponding custom_format.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """

        self.custom_engines[custom_format or '"*/*"'] = (
            content_type, engine, template, exclude_names, render_params or {})

    def lookup_template_engine(self, tgl):
        """Return the template engine data.

        Provides a convenience method to get the proper engine,
        content_type, template, and exclude_names for a particular
        tg_format (which is pulled off of the request headers).

        """
        request = tgl.request
        response = tgl.response

        try:
            render_custom_format = request._render_custom_format[self.controller]
        except:
            render_custom_format = self.render_custom_format

        if render_custom_format:
            (content_type, engine, template, exclude_names, render_params
                ) = self.custom_engines[render_custom_format]
        else:
            if self.default_engine:
                content_type = self.default_engine
            elif self.engines:
                if response.content_type is not None:
                    # Check for overridden content type from the controller call
                    accept_types = create_accept_header(response.content_type)
                elif request._response_type and request._response_type in self.engines:
                    # Check for content type detected by request extensions
                    accept_types = create_accept_header(request._response_type)
                else:
                    accept_types = request.accept

                best_matches = (
                    accept_types.acceptable_offers(self.engines_keys) or
                    # If none of the available engines matches with the
                    # available options, just suggest usage of the first engine.
                    ((self.engines_keys[0], None), )
                )
                content_type = best_matches[0][0]
            else:
                content_type = 'text/html'

            # check for overridden templates
            try:
                cnt_override_mapping = request._override_mapping[self.controller]
                engine, template, exclude_names, render_params = cnt_override_mapping[content_type.split(";")[0]]
            except (AttributeError, KeyError):
                (engine, template, exclude_names, render_params
                    ) = self.engines.get(content_type, (None,) * 4)

        return content_type, engine, template, exclude_names, render_params

    def _register_hook(self, hook_name, func):
        """Registers the specified function as a hook.

        This is internal API which is used by tg.hooks, instead of
        calling this tg.hooks.register should be used.

        We now have four core hooks that can be applied by adding
        decorators: before_validate, before_call, before_render, and
        after_render. register_hook attaches the function to the hook
        which get's called at the appropriate time in the request life
        cycle.)
        """
        self.hooks.setdefault(hook_name, []).append(func)

    def _register_requirement(self, requirement):
        self._register_hook('before_call', requirement._check_authorization)
        self.requirements.append(requirement)

    def _register_controller_wrapper(self, wrapper):
        self.controller_caller = wrapper(self.controller_caller)

    def _register_validation(self, validation):
        self.validations.insert(0, validation)
