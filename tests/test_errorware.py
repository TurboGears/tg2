import time

from webtest import TestApp

from tg import FullStackApplicationConfigurator, TGController, expose
from tg.configurator.components.error_reporting import (
    ErrorReportingConfigurationComponent,
)
from tg.configurator.components.slow_requests import SlowRequestsConfigurationComponent


def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return ['HELLO']


class TestErrorReporterConfig(object):

    middleware_name = 'TraceErrorsMiddleware'

    def _make(self, **options):
        step = ErrorReportingConfigurationComponent()
        conf = dict(('trace_errors.%s' % k, v) for k, v in options.items() if k != 'debug')
        if 'debug' in options:
            conf['debug'] = options['debug']
        step._configure_backlash(conf, None)
        return step._add_middleware(conf, simple_app)

    def test_enable_none(self):
        app = self._make()
        assert app.__class__.__name__ == self.middleware_name
        assert not app.reporters

    def test_enable_false(self):
        app = self._make(enable=False)
        assert app.__class__.__name__ != self.middleware_name

    def test_enable_true(self):
        app = self._make(enable=True)
        assert app.__class__.__name__ == self.middleware_name
        assert not app.reporters

    def test_enable_email(self):
        app = self._make(error_email='user@somedomain.com', 
                         smtp_server="fakeserver", 
                         from_address="fakesender")
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'EmailReporter'
            for r in app.reporters)

    def test_enable_email_requires_options(self):
        try:
            app = self._make(error_email='user@somedomain.com', 
                             from_address="fakesender")
        except ValueError as e:
            assert "smtp_server" in str(e)
        else:
            assert False, "not raised"

    def test_enable_sentry(self):
        app = self._make(sentry_dsn='http://public:secret@example.com/1')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'SentryReporter'
            for r in app.reporters)

    def test_debug_mode(self):
        app = self._make(debug='on', enable=True,
                         error_email='user@somedomain.com')
        assert app is simple_app

    def test_actually_reports(self):
        class RootController(TGController):
            @expose()
            def index(self):
                return 1/0

        REPORTED_CONTEXT = {}
        class Reporter(object):
            def report(self, traceback):
                REPORTED_CONTEXT.update(traceback.context)

        cfg = FullStackApplicationConfigurator()
        cfg.update_blueprint({
            'debug': False,
            'trace_errors.enable': True,
            'trace_errors.reporters': [
                Reporter()
            ],
            'root_controller': RootController()
        })
        app = TestApp(cfg.make_wsgi_app({}, {}))
        app.get('/', status=404, expect_errors=True)

        assert 'request' in REPORTED_CONTEXT


class TestSlowReqsReporterConfig(object):

    middleware_name = 'TraceSlowRequestsMiddleware'

    def _make(self, **options):
        step = SlowRequestsConfigurationComponent()
        conf = dict(('trace_slowreqs.%s' % k, v) for k, v in options.items() if k != 'debug')
        if 'debug' in options:
            conf['debug'] = options['debug']
        step._configure_backlash(conf, None)
        return step._add_middleware(conf, simple_app)

    def test_disable_all(self):
        app = self._make()
        assert app is simple_app

    def test_enable_without_reporter(self):
        app = self._make(enable=True)
        assert app.__class__.__name__ == self.middleware_name
        assert not app.reporters

    def test_enable_email(self):
        app = self._make(enable=True, error_email='user@somedomain.com',
                         smtp_server="fakesmtp", from_address="fakefrom")
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'EmailReporter'
            for r in app.reporters)

    def test_enable_sentry(self):
        app = self._make(enable=True, sentry_dsn='http://public:secret@example.com/1')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'SentryReporter'
            for r in app.reporters)

    def test_debug_mode(self):
        app = self._make(debug='on', enable=True,
                         error_email='user@somedomain.com')
        assert app is simple_app

    def test_backward_compatibility(self):
        conf = {'tg.errorware': {'SOMETHING': True}}

        step = SlowRequestsConfigurationComponent()
        step._configure_backlash(conf, None)

        assert conf['tg.slowreqs']['SOMETHING'] == True

    def test_actually_reports(self):
        class RootController(TGController):
            @expose()
            def index(self):
                # Wait for the slow req reporter to report the request.
                for i in range(100):
                    if 'request' in REPORTED_CONTEXT:
                        break
                    time.sleep(0.01)
                else:
                    assert False, 'Timeout!'
                return 'HI'

        REPORTED_CONTEXT = {}
        class Reporter(object):
            def report(self, traceback):
                REPORTED_CONTEXT.update(traceback.context)

        cfg = FullStackApplicationConfigurator()
        cfg.update_blueprint({
            'debug': False,
            'trace_slowreqs.enable': True,
            'trace_slowreqs.interval': 0,
            'trace_slowreqs.reporters': [
                Reporter()
            ],
            'root_controller': RootController()
        })
        app = TestApp(cfg.make_wsgi_app({}, {}))
        assert app.get('/').text == 'HI'
        assert 'request' in REPORTED_CONTEXT
