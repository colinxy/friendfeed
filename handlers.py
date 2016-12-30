
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
import tornado.auth
import tornado.gen
import tornado.web
import tornado.websocket


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        pass


class FeedsHandler(tornado.web.RequestHandler, tornado.auth.TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        pass


class TwitterStreamHandler(tornado.websocket.WebSocketHandler,
                           tornado.auth.TwitterMixin):
    @tornado.gen.coroutine
    def open(self):
        # TODO
        if self.get_argument("twitter_oauth", None):
            user = yield self.get_authenticated_user()
        else:
            yield self.authorize_redirect()
            return

        request = HTTPRequest(
            "https://stream.twitter.com/1.1/statuses/sample.json",
            method="GET",
            auth_username="",
            streaming_callback=None,
        )
        self.fetch_future = AsyncHTTPClient(request).fetch()

    def on_message(self):
        pass

    def on_close(self):
        pass
