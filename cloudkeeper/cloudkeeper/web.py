from prometheus_client.exposition import generate_latest, CONTENT_TYPE_LATEST
from cloudkeeper.args import ArgumentParser
from cloudkeeper.event import Event, EventType, add_event_listener, dispatch_event
import cherrypy
import threading
import cloudkeeper.logging

log = cloudkeeper.logging.getLogger(__name__)


class CloudkeeperWebApp:
    def __init__(self, gc) -> None:
        self.gc = gc

    @cherrypy.expose
    def index(self):
        return "Cloudkeeper"

    @cherrypy.expose
    def health(self):
        cherrypy.response.headers["Content-Type"] = "text/plain"
        return "ok\r\n"

    @cherrypy.expose
    def metrics(self):
        cherrypy.response.headers["Content-Type"] = CONTENT_TYPE_LATEST
        return generate_latest()

    @cherrypy.expose
    def graph(self):
        cherrypy.response.headers["Content-Type"] = "application/octet-stream"
        return self.gc.pickle

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def collect(self):
        if ArgumentParser.args.web_psk:
            if not hasattr(cherrypy.request, "json"):
                raise cherrypy.HTTPError(400, "Invalid JSON request")
            data = cherrypy.request.json
            if (
                not isinstance(data, dict)
                or data.get("psk") != ArgumentParser.args.web_psk
            ):
                raise cherrypy.HTTPError(401, "Invalid PSK")
        dispatch_event(Event(EventType.START_COLLECT))
        return {"status": "ok"}

    @cherrypy.expose
    def graph_gexf(self):
        cherrypy.response.headers["Content-Type"] = "application/xml; charset=utf-8"
        return str(self.gc.gexf).encode("utf-8")

    @cherrypy.expose
    def graph_graphml(self):
        cherrypy.response.headers["Content-Type"] = "application/xml; charset=utf-8"
        return str(self.gc.graphml).encode("utf-8")

    @cherrypy.expose
    def graph_json(self):
        cherrypy.response.headers["Content-Type"] = "application/json; charset=utf-8"
        return str(self.gc.json).encode("utf-8")

    @cherrypy.expose
    def graph_net(self):
        cherrypy.response.headers["Content-Type"] = "text/plain"
        return self.gc.pajek

    @cherrypy.expose
    def graph_txt(self):
        cherrypy.response.headers["Content-Type"] = "text/plain"
        return self.gc.text


class WebServer(threading.Thread):
    def __init__(self, gc) -> None:
        super().__init__()
        self.name = "webserver"
        self.gc = gc
        add_event_listener(EventType.SHUTDOWN, self.shutdown)

    def run(self) -> None:
        cherrypy.engine.unsubscribe("graceful", cherrypy.log.reopen_files)
        cherrypy.tree.mount(
            CloudkeeperWebApp(self.gc),
        )
        cherrypy.config.update(
            {
                "global": {
                    "engine.autoreload.on": False,
                    "server.socket_port": ArgumentParser.args.web_port,
                    "log.screen": False,
                    "log.access_file": "",
                    "log.error_file": "",
                    "tools.encode.on": True,
                    "tools.encode.encoding": "utf-8",
                }
            }
        )
        cherrypy.engine.start()
        cherrypy.engine.block()

    def shutdown(self, event: Event):
        log.debug(
            f"Received request to shutdown http server threads {event.event_type}"
        )
        cherrypy.engine.exit()

    @staticmethod
    def add_args(arg_parser: ArgumentParser) -> None:
        arg_parser.add_argument(
            "--web-port",
            help="Web Port (default 8000)",
            default=8000,
            dest="web_port",
            type=int,
        )
        arg_parser.add_argument(
            "--web-psk",
            help="Pre Shared Key for /collect requests",
            default=None,
            dest="web_psk",
            type=str,
        )
