
from tornado.auth import FacebookGraphMixin
import tornado.web
import tornado.gen


class FacebookLogin(tornado.web.RequestHandler, FacebookGraphMixin):
    @tornado.gen.coroutine
    def get(self):
        pass


class FacebookLogout(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie
        pass
