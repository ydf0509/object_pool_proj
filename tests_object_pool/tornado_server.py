import tornado.ioloop
import tornado.web
import asyncio


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        # await asyncio.sleep(0.5)
        self.write("Hello, world")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
