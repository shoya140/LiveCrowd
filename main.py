import time
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado import websocket
import os
import MySQLdb
import json
import threading
from tornado.options import define, options

define("port", default=8000, help="run on the given port", type=int)
define("debug", default=0, help="1:watch in real time (debug mode)", type=bool)

config = {}
froyer_count = 0
showroom_count = 0

class SQLThread(threading.Thread):
    import MySQLdb

    def __init__(self):
        threading.Thread.__init__(self)

        self.ignore_device_list = []
        file = open('./ignore.txt')
        lines = file.readlines()
        for line in lines:
            self.ignore_device_list.append(line.rstrip('\n'))
        file.close()

        self.connection_foyer = MySQLdb.connect(
            db=config['foyer']['db'],
            host=config['foyer']['host'],
            port=int(config['foyer']['port']),
            user=config['foyer']['user'],
            passwd=config['foyer']['passwd'])
        self.cursor_foyer = self.connection_foyer.cursor()
        self.connection_showroom = self.MySQLdb.connect(
                db=config['showroom']['db'],
                host=config['showroom']['host'],
                port=int(config['showroom']['port']),
                user=config['showroom']['user'],
                passwd=config['showroom']['passwd'])
        self.cursor_showroom = self.connection_showroom.cursor()
        self.query = "SELECT * FROM "+config['foyer']['table']+" WHERE TimeStamp > TIMESTAMPADD(SECOND, -120, CURRENT_TIMESTAMP())"

    def run(self):
        while 1:
            self.cursor_foyer.execute(self.query)
            result = self.cursor_foyer.fetchall()
            global froyer_count
            froyer_count = self.count("Froyer", result)

            time.sleep(2)

            self.cursor_showroom.execute(self.query)
            result = self.cursor_showroom.fetchall()
            global showroom_count
            showroom_count = self.count("showroom", result)

            time.sleep(2)

    def count(self, name, result):
        print "--"+name+"--"
        dict = {}
        last_device = ""
        for row in result:
            device = row[2]
            if device not in self.ignore_device_list and device != last_device:
                res = ""
                dict.update({row[2]:"dummy"})
                for val in row:
                    res+= str(val)+" "
                print res
            last_device = device
        return len(dict)


class DataWebSocket(websocket.WebSocketHandler):
    def open(self):
        self.send_data()

    def send_data(self):
        self.write_message({'froyer':froyer_count, 'showroom':showroom_count})
        tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 5, self.send_data)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html', url="", title="Live Crowd Density Visualization")

if __name__ == "__main__":
    file = open('./config.json')
    config = json.load(file)
    file.close()

    th = SQLThread()
    th.start()

    tornado.options.parse_command_line()
    app = tornado.web.Application(
            debug=options.debug,
            handlers=[
                (r"/", IndexHandler),
                (r"/data/", DataWebSocket)],
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static")
            )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
