from tg.configuration.sqla.balanced_session import BalancedSession, UsingEngineContext, force_request_engine
from tg.util import Bunch
from tg.wsgiapp import RequestLocals
from tg import request_local
import tg

class TestBalancedSession(object):
    def setup(self):
        locals = RequestLocals()
        locals.request = Bunch()
        locals.app_globals = Bunch()
        locals.config = Bunch({'tg.app_globals':locals.app_globals,
                               'balanced_engines': {'all':{'master':'master',
                                                            'slave1':'slave1',
                                                            'slave2':'slave2'},
                                                    'master':'master',
                                                    'slaves':{'slave1':'slave1',
                                                              'slave2':'slave2'}}})

        #Register Global objects
        request_local.config._push_object(locals.config)
        request_local.context._push_object(locals)

        self.locals = locals
        self.session = BalancedSession()
        locals.config['DBSession'] = self.session

    def teardown(self):
        request_local.config._pop_object()
        request_local.context._pop_object()

    def test_disabled_balancing(self):
        tg.config['balanced_engines'] = None
        tg.app_globals['sa_engine'] = 'DEFAULT_ENGINE'
        assert self.session.get_bind() == 'DEFAULT_ENGINE'

    def test_disabled_balancing_out_of_request(self):
        request_local.context._pop_object()
        tg.config['balanced_engines'] = None
        tg.config['tg.app_globals']['sa_engine'] = 'DEFAULT_ENGINE'
        assert self.session.get_bind() == 'DEFAULT_ENGINE'
        request_local.context._push_object(self.locals)

    def test_master_on_flush(self):
        self.session._flushing = True
        assert self.session.get_bind() == 'master'

    def test_master_out_of_request(self):
        request_local.context._pop_object()
        assert self.session.get_bind() == 'master'
        request_local.context._push_object(self.locals)

    def test_pick_slave(self):
        assert self.session.get_bind().startswith('slave')

    def test_with_context(self):
        with self.session.using_engine('master'):
            assert self.session.get_bind() == 'master'
        assert self.session.get_bind().startswith('slave')

    def test_forced_engine(self):
        force_request_engine('slave2')
        assert self.session.get_bind() == 'slave2'

    def test_with_explicit_context(self):
        class FakeThreadedSession:
            def __init__(self, real_session):
                self.sess = real_session
            def __call__(self):
                return self.sess

        self.locals.config['DBSession'] = FakeThreadedSession(self.session)
        with UsingEngineContext('master'):
            assert self.session.get_bind() == 'master'
        assert self.session.get_bind().startswith('slave')
