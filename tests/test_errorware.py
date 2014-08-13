from tg.error import ErrorReporter
from tg.error import SlowReqsReporter


def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return ['HELLO']


class TestErrorReporterConfig(object):

    middleware_name = 'TraceErrorsMiddleware'

    def test_enable_none(self):
        app = ErrorReporter(simple_app, {})
        assert app.__class__.__name__ == self.middleware_name
        assert not app.reporters

    def test_enable_email(self):
        app = ErrorReporter(simple_app, {},
            error_email='user@somedomain.com')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'EmailReporter'
            for r in app.reporters)

    def test_enable_sentry(self):
        app = ErrorReporter(simple_app, {},
            sentry_dsn='http://public:secret@example.com/1')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'SentryReporter'
            for r in app.reporters)

    def test_debug_mode(self):
        app = ErrorReporter(simple_app, dict(debug='on'), enable=True,
            error_email='user@somedomain.com')
        assert app is simple_app


class TestSlowReqsReporterConfig(object):

    middleware_name = 'TraceSlowRequestsMiddleware'

    def test_disable_all(self):
        app = SlowReqsReporter(simple_app, {})
        assert app is simple_app

    def test_enable_without_reporter(self):
        app = SlowReqsReporter(simple_app, {}, enable=True)
        assert app.__class__.__name__ == self.middleware_name
        assert not app.reporters

    def test_enable_email(self):
        app = SlowReqsReporter(simple_app, {}, enable=True,
            error_email='user@somedomain.com')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'EmailReporter'
            for r in app.reporters)

    def test_enable_sentry(self):
        app = SlowReqsReporter(simple_app, {}, enable=True,
            sentry_dsn='http://public:secret@example.com/1')
        assert app.__class__.__name__ == self.middleware_name
        assert any(r.__class__.__name__ == 'SentryReporter'
            for r in app.reporters)

    def test_debug_mode(self):
        app = SlowReqsReporter(simple_app, dict(debug='on'), enable=True,
            error_email='user@somedomain.com')
        assert app is simple_app
