
import tornado.ioloop
import tornado.gen
import tornado.web
from tornado.web import URLSpec as url
import motor.motor_tornado

from tornado.log import enable_pretty_logging
from tornado.options import (define, options,
                             parse_config_file, parse_command_line)

from bson import json_util
import os.path
import json

import handlers
import twitter


_BASE_DIR = os.path.dirname(__file__)

define("port", default=80)
define("ip", default="0.0.0.0")
define("config_dir", default=_BASE_DIR)
define("debug", default=False)

define("template_path", type=str,
       default=os.path.join(_BASE_DIR, "templates"))
define("static_path", type=str,
       default=os.path.join(_BASE_DIR, "static"))
define("database_collection", type=str, default="friendfeed")
# cookie
define("cookie_secret", type=str)
# twitter
define("twitter_consumer_key", type=str, group="twitter")
define("twitter_consumer_secret", type=str, group="twitter")


class TestHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        db = self.settings["db"]
        cursor = db.restaurants.find({"grades.score": {"$gt": 80}})\
                               .sort("name")
        while (yield cursor.fetch_next):
            doc = cursor.next_object()
            # print(doc)
            self.write(json.dumps(doc, default=json_util.default, indent=4))
            self.write("\n\n")
        self.set_header("Content-Type", "text/plain")


def main():
    parse_command_line(final=False)
    parse_config_file(os.path.join(options.config_dir, "friendfeed.cfg"),
                      final=False)
    parse_config_file(os.path.join(options.config_dir, "secrets.cfg"),
                      final=False)
    define("xsrf_cookies", default=True)
    define("db", default=getattr(motor.motor_tornado.MotorClient(),
                                 options.database_collection))

    if options.debug:
        enable_pretty_logging()
    # print(options.as_dict())

    app = tornado.web.Application([
        url(r"/", handlers.MainHandler),
        url(r"/test", TestHandler),

        # twitter
        url(r"/login/twitter", twitter.TwitterLogin, name="twitter_login"),
        url(r"/logout/twitter", twitter.TwitterLogout, name="twitter_logout"),
        url(r"/feed/twitter", twitter.TwitterFeedHandler,
            name="twitter_feed"),
        url(r"/stream/twitter", twitter.TwitterStreamHandler,
            name="twitter_stream"),
        url(r"/test/twitter", twitter.TwitterStreamTest),

        # facebook
    ], **options.as_dict())
    app.listen(options.port, options.ip)


if __name__ == '__main__':
    main()
    tornado.ioloop.IOLoop.current().start()
