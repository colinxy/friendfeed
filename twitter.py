
from tornado.auth import TwitterMixin
import tornado.web
import tornado.gen


class TwitterLogin(tornado.web.RequestHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        pass


class TwitterLogout(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie
        pass
