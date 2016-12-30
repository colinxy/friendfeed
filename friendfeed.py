
import tornado.ioloop
import tornado.gen
import tornado.web
import motor.motor_tornado

from tornado.options import (define, options,
                             parse_config_file, parse_command_line)

from bson import json_util
import os.path
import json

define("port", default=8080)
define("ip", default="localhost")
define("config_dir", default=os.path.dirname(__file__))

define("template_path", type=str,
       default=os.path.join(os.path.dirname(__file__), "templates"))
define("static_path", type=str,
       default=os.path.join(os.path.dirname(__file__), "static"))
define("database_collection", type=str,
       default="test")
define("twitter_consumer_key", type=str, group="twitter")
define("twitter_consumer_secret", type=str, group="twitter")


class MainHandler(tornado.web.RequestHandler):
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
    settings = dict(
        template_path=options.template_path,
        static_path=options.static_path,
        # db=motor.motor_tornado.MotorClient().test,  # test database
        db=getattr(motor.motor_tornado.MotorClient(),
                   options.database_collection),
    )
    # print(options.as_dict())

    app = tornado.web.Application([
        (r"/", MainHandler),
    ], **settings)
    app.listen(options.port, options.ip)


if __name__ == '__main__':
    main()
    tornado.ioloop.IOLoop.current().start()
