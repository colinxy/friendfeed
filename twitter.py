
from __future__ import print_function

from tornado.auth import TwitterMixin
from tornado.escape import json_decode, json_encode
from tornado.httpclient import AsyncHTTPClient
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
        self.render("twitter.html", timeline=timeline)


class TwitterStreamTest(TwitterBaseHandler, tornado.auth.TwitterMixin):
    http_client = None

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        self.tweets_partial = b""       # each twitter json response
        self.set_header("Content-Type", "text/plain")
        self.stream_future = self.twitter_request(
            "https://stream.twitter.com/1.1/statuses/filter.json",
            post_args={"track": "sherlock"},  # due to its popularity
            access_token=self.current_user["access_token"],
        )
        yield self.stream_future

    def get_auth_http_client(self):
        """override to use long lived http request (for twitter_request).
        Ugly hack to make special HTTPRequest object
        work with twitter_request.
        self.http_client shared among all instances
        """
        if self.http_client is None:
            # defaults passed onto HTTPRequest
            self.http_client = AsyncHTTPClient(
                defaults=dict(streaming_callback=self.on_chunk,
                              force_instance=True,
                              connect_timeout=600,  # 10mins
                              request_timeout=600,)
            )
        return self.http_client

    def on_chunk(self, chunk):
        """flush tweet id to user"""
        # chunk: byte string
        self.tweets_partial += chunk
        # print(chunk, end="\n\n")

        idx_begin = 0
        idx_end = self.tweets_partial.find(b"\r\n")
        while idx_end != -1:
            tweet_json = json_decode(self.tweets_partial[idx_begin:idx_end])
            self.write(tweet_json["id_str"] + "\r\n")
            print(tweet_json["id_str"])
            self.flush()

            idx_begin = idx_end + 2
            idx_end = self.tweets_partial.find(b"\r\n", idx_begin)

        self.tweets_partial = self.tweets_partial[idx_begin:]

    def on_connection_close(self):
        print("<client close connection>")
        # bad news! tornado Future cannot be cancelled
        self.stream_future.cancel()


class TwitterStreamHandler(TwitterBaseHandler,
                           tornado.websocket.WebSocketHandler,
                           tornado.auth.TwitterMixin):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def open(self):
        yield self.twitter_request(
            "https://stream.twitter.com/1.1/statuses/sample.json",
            access_token=self.current_user["access_token"],
        )

    def on_message(self):
        pass

    def on_close(self):
        pass
