class DummyMiddleware(object):

    def __init__(self, app, flag):
        self.app = app
        self.flag = flag

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            start_response("200 OK", [("X-LYMPH-TEST", self.flag)])
            return ['Yay!']
        return self.app(environ, start_response)
