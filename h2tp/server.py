import socketserver
from typing import Callable

from .base import HEADER_IDS, BaseH2TPRequest, H2TPData
from .util import Log, normalize_path


class Response(BaseH2TPRequest):
    DEFAULT_CLIENT_ID = b"Python/h2tp (server)"

    def __init__(
        self,
        body: str | bytes | None=None,
        headers: dict[int, str | bytes | tuple[str | bytes, bool]] | None=None,
        compress: bool=False,
        corrupted: bool=False
    ):
        super().__init__(body, headers, compress)

        self.corrupted = corrupted

        if HEADER_IDS.CLIENT_ID not in self.headers:
            self.headers[HEADER_IDS.CLIENT_ID] = (self.DEFAULT_CLIENT_ID, HEADER_IDS.CLIENT_ID in HEADER_IDS.META.IMPORTANT_HEADERS)

class H2TPRequestHandler(socketserver.BaseRequestHandler):
    H2TP_SERVER = None

    @staticmethod
    def h2tp_link_server(server: "Server"):
        H2TPRequestHandler.H2TP_SERVER = server

    def handle(self):
        if self.H2TP_SERVER is None:
            raise TypeError("H2TP request handler doesn't have server context")

        sock = self.request
        data = BaseH2TPRequest.get_from_stream(sock)
        parsed = BaseH2TPRequest.parse(data)

        Log.debug("[H2TP Server]", parsed)

        if parsed is None:
            Log.err("[H2TP Server] Failed to parse request")
            sock.sendall(Response(corrupted=True).build_request())
            return

        hostname = bytes.decode(parsed.headers[HEADER_IDS.HOST].content, errors="ignore") if HEADER_IDS.HOST in parsed.headers else None
        path = bytes.decode(parsed.headers[HEADER_IDS.PATH].content, errors="ignore") if HEADER_IDS.PATH in parsed.headers else None

        Log.info(f"{path} @ {hostname} (from {':'.join([str(i) for i in self.client_address])})")

        rt = self.H2TP_SERVER.ROUTING_TABLE

        try:
            if HEADER_IDS.PATH in parsed.headers:
                path = normalize_path(bytes.decode(parsed.headers[HEADER_IDS.PATH].content))

                if path in rt:
                    sock.sendall(rt[path](data).build_request())
                elif not path.endswith("/") and (path + "/") in rt:
                    sock.sendall(rt[path + "/"](data).build_request())

            if "*" in rt:
                sock.sendall(rt["*"](data).build_request())

        except BaseException as err:
            Log.info("[H2TP Server] Internal Server Error", err)
            sock.sendall(Response(headers={
                HEADER_IDS.STATUS: b"500 Internal Server Error"
            }).build_request())
            return

        sock.sendall(Response(headers={
            HEADER_IDS.STATUS: b"404 Not Found"
        }).build_request())

class Server:
    def __init__(self):
        self.ROUTING_TABLE: dict[str, Callable[[bytes], Response]] = {}

    def run(self, hostname: str="127.0.0.1", port: int=2220):
        sock = socketserver.TCPServer((hostname, port), H2TPRequestHandler)
        H2TPRequestHandler.h2tp_link_server(self)

        Log.info("[H2TP Server] Listening on", hostname, "with port", port)

        try:
            sock.serve_forever()
        except KeyboardInterrupt:
            Log.info("[H2TP Server] Exiting")

    def router(self, path: str="*"):
        def decorator(f: Callable[[H2TPData], Response | bytes | str]):
            def wrapper(data: bytes) -> Response:
                parsed: H2TPData | None = Response.parse(data)

                if parsed is None:
                    return Response(corrupted=True)

                response = f(parsed)

                if isinstance(response, Response):
                    return response
                elif isinstance(response, str):
                    response = str.encode(response)

                return Response(response)

            self.ROUTING_TABLE[path] = wrapper
            wrapper.__name__ = "h2tp_decorator__" + path

            return wrapper
        return decorator
