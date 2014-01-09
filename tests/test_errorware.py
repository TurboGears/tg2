from tg.error import ErrorReporter


def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return ['HELLO']


class TestErrorReporterConfig(object):
    def test_disable_all(self):
        app = ErrorReporter(simple_app, {})
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'EmailReporter' not in reporters
        assert 'SentryReporter' not in reporters

    def test_enable_email(self):
        app = ErrorReporter(simple_app, {}, error_email='user@somedomain.com')
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'EmailReporter' in reporters

    def test_enable_sentry(self):
        app = ErrorReporter(simple_app, {}, sentry_dsn='http://public:secret@example.com/1')
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'SentryReporter' in reporters
