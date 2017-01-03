
from __future__ import print_function

from tornado.auth import TwitterMixin
from tornado.escape import json_decode, json_encode
from tornado.httpclient import AsyncHTTPClient, HTTPError
import tornado.gen
import tornado.log
import tornado.web
import tornado.websocket

import json


class TwitterBaseHandler(tornado.web.RequestHandler):
    _TWITTER_COOKIE = "twitter_user"

    def get_current_user(self):
        user_json_bytes = self.get_secure_cookie(self._TWITTER_COOKIE)
        # print(json.dumps(json_decode(user_json_bytes), indent=4))
        if not user_json_bytes:
            return None
        user_json = json_decode(user_json_bytes)
        return user_json        # self._filter_user_json(user_json)

    def _filter_user_json(self, user_json):
        return dict(username=user_json["username"],
                    name=user_json["name"],
                    id_str=user_json["id_str"],
                    access_token=user_json["access_token"])

    def get_login_url(self):
        return self.reverse_url("twitter_login")


class TwitterLogin(TwitterBaseHandler, TwitterMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.current_user:
            self.redirect(self.reverse_url("twitter_feed"))

        # 3-phase OAuth
        if self.get_argument("oauth_token", None):
            user = yield self.get_authenticated_user()
            # cookie: path='/'
            self.set_secure_cookie(self._TWITTER_COOKIE,
                                   json_encode(self._filter_user_json(user)))
            # print(user)
            self.redirect(self.reverse_url("twitter_feed"))
        else:
            yield self.authorize_redirect()


class TwitterLogout(TwitterBaseHandler):
    def get(self):
        self.clear_cookie(self._TWITTER_COOKIE)
        self.redirect("/")


class TwitterFeedHandler(TwitterBaseHandler, TwitterMixin):
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


class TwitterStreamMixin(TwitterBaseHandler, TwitterMixin):
    # refer to https://dev.twitter.com/streaming/overview/connecting
    # for more complete HTTP Error Codes description
    TWITTER_STREAMING_ERRORS = {
        401: "Unauthorized",
        403: "Forbidden",
        404: "Unknown",
        406: "Not Acceptable",
        413: "Too Long",
        416: "Range Unacceptable",
        420: "Rate Limited",
        503: "Service Unavailable",
    }

    http_client = None

    @tornado.gen.coroutine
    def stream(self, path, post_args=None):
        self.tweets_partial = b""  # each twitter json response
        self.streaming = True      # False on_connection_close

        while self.streaming:
            self.stream_future = self.twitter_request(
                path,
                post_args=post_args,
                access_token=self.current_user["access_token"],
            )
            try:
                yield self.stream_future
            except tornado.httpclient.HTTPError as err:
                # only catch 599 timeout error
                if err.code != 599:
                    self.on_error(err)
                # print("==> reconnectiong")

    def on_error(self, err):
        """Called when twitter streaming error occurs.
        """
        raise NotImplementedError()

    def on_chunk(self, chunk):
        """Called when data arrives from stream.
        Based on twitter streaming documentation
        https://dev.twitter.com/streaming/overview/processing,
        each valid json response is delimited by b"\r\n".
        """
        # print(type(chunk))
        # chunk: byte string, each chunk might be incomplete json
        self.tweets_partial += chunk
        # print(chunk, end="\n\n")

        i_beg = 0
        i_end = self.tweets_partial.find(b"\r\n")
        while i_end != -1:
            try:
                tweet_json = json_decode(self.tweets_partial[i_beg:i_end])
            except json.decoder.JSONDecodeError as err:
                # print(self.tweets_partial[i_beg:i_end])
                tornado.log.app_log.exception(err)
                self.streaming = False
                break

            # print(tweet_json)
            self.on_json(tweet_json)
            i_beg = i_end + 2
            i_end = self.tweets_partial.find(b"\r\n", i_beg)

        self.tweets_partial = self.tweets_partial[i_beg:]

    def on_json(self, chunk_json):
        """Called when a valid json response arrives from stream.
        Note it is overrider's responsibility to flush response.
        """
        raise NotImplementedError()

    def on_connection_close(self):
        """Override ``tornado.web.RequestHandler.on_connection_close``
        to handle terminating twitter streaming.
        """
        # print("==> client close connection")
        # bad news! tornado Future cannot be cancelled
        # self.stream_future.cancel()
        # use short connection timeout and reconnect
        self.streaming = False

    def _on_twitter_request(self, future, response):
        """Override ``tornado.auth.TwitterMixin._on_twitter_request``
        to throw httpclient.HTTPError instead of auth.AuthError.
        """
        if response.error:
            future.set_exception(
                HTTPError(response.code,
                          "Error response {} fetching {}"
                          .format(response.error, response.request.url))
            )
            return
        future.set_result(json_decode(response.body))

    def get_auth_http_client(self):
        """Override ``tornado.auth.OAuthMixin.get_auth_http_client``
        to use long lived http request client.
        Create a special HTTPRequest object to work with twitter_request
        without interfering other HTTPRequest. Note self.http_client
        is shared among all twitter streaming instances
        """
        if self.http_client is None:
            # defaults passed onto HTTPRequest
            self.http_client = AsyncHTTPClient(
                defaults=dict(streaming_callback=self.on_chunk,
                              force_instance=True,
                              connect_timeout=300,
                              request_timeout=300,)
            )
        return self.http_client


class TwitterStreamTest(TwitterStreamMixin,
                        TwitterBaseHandler,
                        TwitterMixin):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        self.set_header("Content-Type", "text/plain")
        yield self.stream(
            "https://stream.twitter.com/1.1/statuses/filter.json",
            post_args={"track": "sherlock"},  # due to its popularity
        )

    def on_json(self, tweet_json):
        self.write(tweet_json["id_str"] + "\r\n")
        self.flush()

    def on_error(self, err):
        if err.code in self.TWITTER_STREAMING_ERRORS:
            tornado.log.app_log.error(
                "Twitter Streaming Error {} {}: {}"
                .format(err.code,
                        self.TWITTER_STREAMING_ERRORS[err.code],
                        err.message))
        elif err.code != 599:
            tornado.log.app_log.error(
                "Twitter Streaming Error {}: {}"
                .format(err.code,
                        err.message))
        raise err


class TwitterStreamHandler(tornado.websocket.WebSocketHandler,
                           TwitterStreamMixin,
                           TwitterBaseHandler,
                           TwitterMixin):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def open(self):
        yield self.stream(
            "https://stream.twitter.com/1.1/statuses/filter.json",
            post_args={"track": "sherlock"},  # due to its popularity
        )

    def on_json(self, tweet_json):
        self.write_message(dict(
            id_str=tweet_json["id_str"],
            user_screen_name=tweet_json["user"]["screen_name"],
            text=tweet_json["text"],
        ))

    def on_message(self):
        pass

    def on_close(self):
        self.streaming = False
