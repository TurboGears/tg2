from tg.configuration.configurator.steps.error_reporting import ErrorReportingConfigurationComponent
from tg.configuration.configurator.steps.slow_requests import SlowRequestsConfigurationComponent

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
        app = self._make(error_email='user@somedomain.com')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'EmailReporter'
            for r in app.reporters)

    def test_enable_sentry(self):
        app = self._make(sentry_dsn='http://public:secret@example.com/1')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'SentryReporter'
            for r in app.reporters)

    def test_debug_mode(self):
        app = self._make(debug='on', enable=True,
                         error_email='user@somedomain.com')
        assert app is simple_app


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
        app = self._make(enable=True, error_email='user@somedomain.com')
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
