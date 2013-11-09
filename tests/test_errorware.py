from tg.error import ErrorReporter


def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return ['HELLO']


class TestErrorReporterConfig(object):
    def test_disable_email(self):
        app = ErrorReporter(simple_app, {}, disable_email=True)
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'EmailReporter' not in reporters

    def test_enable_sentry(self):
        app = ErrorReporter(simple_app, {}, enable_sentry=True, sentry_dsn='')
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'SentryReporter' in reporters