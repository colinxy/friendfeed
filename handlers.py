
import tornado.auth
import tornado.gen
import tornado.web
import tornado.websocket


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        self.render("index.html")


class FeedsHandler(tornado.web.RequestHandler, tornado.auth.TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        pass
