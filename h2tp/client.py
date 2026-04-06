from socket import socket

from .base import HEADER_IDS, BaseH2TPRequest, H2TPData
from .util import Log


class Request(BaseH2TPRequest):
    DEFAULT_CLIENT_ID = b"Python/h2tp (client)"

    def __init__(
        self,
        url: str, # format: h2tp://<domain>[:<port>]/[path]
        body: str | bytes | None=None,
        headers: dict[int, str | bytes | tuple[str | bytes, bool]] | None=None,
        compress: bool=False,
        overwrite_necessary_headers: bool=True
    ):
        # super handles standardizing headers, body, compression
        super().__init__(body, headers, compress)

        # append trailing slash if missing on just domain
        if url.count("/") < 3:
            url = url + "/"

        self.url: str = url
        self.protocol: str = url.split("://")[0].lower()
        self.hostname: str = url.split("://")[1].split("/")[0]
        self.path: str = "/" + url.split("/", 3)[-1]

        if ":" in self.hostname:
            self.port = int(self.hostname.split(":")[1])
            self.hostname = self.hostname.split(":")[0]
        else:
            self.port = 2

        if self.protocol != "h2tp":
            Log.warn(f"Protocol {self.protocol}:// isn't h2tp:// - continuing anyways")

        # add default headers
        if overwrite_necessary_headers or HEADER_IDS.HOST not in self.headers:
            self.headers[HEADER_IDS.HOST] = (str.encode(self.hostname), HEADER_IDS.HOST in HEADER_IDS.META.IMPORTANT_HEADERS)

        if overwrite_necessary_headers or HEADER_IDS.PATH not in self.headers:
            self.headers[HEADER_IDS.PATH] = (str.encode(self.path), HEADER_IDS.PATH in HEADER_IDS.META.IMPORTANT_HEADERS)

        if HEADER_IDS.CLIENT_ID not in self.headers:
            self.headers[HEADER_IDS.CLIENT_ID] = (self.DEFAULT_CLIENT_ID, HEADER_IDS.CLIENT_ID in HEADER_IDS.META.IMPORTANT_HEADERS)

    def send(self) -> H2TPData | None:
        with socket() as sock:
            sock.connect((self.hostname, self.port))
            sock.sendall(self.build_request())

            response = self.get_from_stream(sock)
            parsed = self.parse(response)
            Log.debug("[H2TP Server]", parsed)

            return parsed

def fetch(
    url: str,
    body: str | bytes | None=None,
    headers: dict[int, str | bytes | tuple[str | bytes, bool]] | None=None
) -> H2TPData | None:
    # Easy wrapper for `Request`s

    obj = Request(url, body, headers)
    return obj.send()
