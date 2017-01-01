
from tornado.auth import TwitterMixin
from tornado.escape import json_decode, json_encode
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
import tornado.gen
import tornado.web
import tornado.websocket


class TwitterBaseHandler(tornado.web.RequestHandler):
    _TWITTER_COOKIE = "twitter_user"

    def get_current_user(self):
        user_json = self.get_secure_cookie(self._TWITTER_COOKIE)
        if not user_json:
            return None
        return json_decode(user_json)

    def get_login_url(self):
        return self.reverse_url("twitter_login")


class TwitterLogin(TwitterBaseHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            # cookie: path='/'
            self.set_secure_cookie(self._TWITTER_COOKIE, json_encode(user))
            # print(user)
            self.redirect(self.reverse_url("twitter_feed"))
        else:
            yield self.authorize_redirect()


class TwitterLogout(TwitterBaseHandler):
    def get(self):
        self.clear_cookie(self._TWITTER_COOKIE)
        self.redirect("/")


class TwitterHandler(TwitterBaseHandler, TwitterMixin):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        # print(self.current_user)
        timeline = yield self.twitter_request(
            "/statuses/home_timeline",
            access_token=self.current_user["access_token"]
        )
        # print(timeline)
        self.render("twitter.html",
                    timeline=timeline,
                    tweet_ids=json_encode([t["id"] for t in timeline]))


class TwitterStreamHandler(TwitterBaseHandler,
                           tornado.websocket.WebSocketHandler,
                           tornado.auth.TwitterMixin):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def open(self):
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
