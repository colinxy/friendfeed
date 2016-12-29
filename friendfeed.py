
import tornado.ioloop
import tornado.gen
import tornado.web
import motor.motor_tornado

from bson import json_util
import json


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


settings = {
    "template_path": "templates",
    "static_path": "static",
    "db": motor.motor_tornado.MotorClient().test,  # test database
    # "db": motor.motor_tornado.MotorClient().friendfeed,
}

app = tornado.web.Application([
    (r"/", MainHandler),
], **settings)

if __name__ == '__main__':
    app.listen(8080, "localhost")
    tornado.ioloop.IOLoop.current().start()
