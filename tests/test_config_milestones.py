from nose.tools import raises
from tg._compat import im_self
from tg.configuration.milestones import _ConfigMilestoneTracker, config_ready
from tg.configuration.utils import GlobalConfigurable, TGConfigError


class Action:
    called = 0
    def __call__(self):
        self.called += 1


class TestMilestones(object):
    def setup(self):
        self.milestone = _ConfigMilestoneTracker('test_milestone')

    def test_multiple_registration(self):
        a = Action()
        self.milestone.register(a)
        self.milestone.register(a)
        self.milestone.register(a)

        self.milestone.reach()
        assert a.called == 1

    def test_register_after_reach(self):
        a = Action()

        self.milestone.reach()
        self.milestone.register(a)
        assert a.called == 1

    def test_call_all(self):
        a = Action()
        a2 = Action()
        a3 = Action()

        self.milestone.register(a)
        self.milestone.register(a2)
        self.milestone.register(a3)

        self.milestone.reach()
        assert a.called == a2.called == a3.called == 1

    def test_register_func_unique(self):
        called = []
        def f():
            called.append(True)

        self.milestone.register(f)
        self.milestone.register(f)

        self.milestone.reach()
        assert len(called) == 1


class TemporaryGlobalConfigurable(GlobalConfigurable):
    pass

class TestGlobalConfigurable(object):
    def setup(self):
        config_ready._reset()

    def teardown(self):
        for action in config_ready._keep_on_reset[:]:
            default_object = im_self(action)
            if default_object and isinstance(default_object, TemporaryGlobalConfigurable):
                config_ready._keep_on_reset.remove(action)

        config_ready._reset()

    @raises(NotImplementedError)
    def test_requires_configure_implementation(self):
        class NoConfig(TemporaryGlobalConfigurable):
            CONFIG_NAMESPACE = 'fake.'

        default_object = NoConfig.create_global()
        config_ready.reach()

    @raises(TGConfigError)
    def test_requires_namespace(self):
        class NoNameSpace(TemporaryGlobalConfigurable):
            def configure(self, **options):
                return options

        default_object = NoNameSpace.create_global()
        config_ready.reach()

    def test_gets_configured_on_config_ready(self):
        class Configurable(TemporaryGlobalConfigurable):
            CONFIG_NAMESPACE = 'fake.'
            _CONFIGURED = []

            def configure(self, **options):
                self._CONFIGURED.append(True)

        default_object = Configurable.create_global()
        config_ready.reach()

        assert len(Configurable._CONFIGURED) == 1

    def test_keeps_on_milestone_reset(self):
        class Configurable(TemporaryGlobalConfigurable):
            CONFIG_NAMESPACE = 'fake.'
            _CONFIGURED = []

            def configure(self, **options):
                self._CONFIGURED.append(True)

        default_object = Configurable.create_global()
        config_ready.reach()

        config_ready._reset()
        config_ready.reach()

        assert len(Configurable._CONFIGURED) == 2