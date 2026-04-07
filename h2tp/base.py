import socket

from .util import Log, b, clamp


class HEADER_IDS:
    HOST = 0x00 # domain, ex. "google.com"
    PATH = 0x01 # ex. "/api/abcdefg"
    CLIENT_ID = 0x02 # user agent, ex. "Python/h2tp"
    MIME_TYPE = 0x03 # ex. "text/h2ml"
    STATUS = 0x04 # ex. "200 OK"

    class META:
        IMPORTANT_HEADERS = [
            0x00, # HOST
            0x01, # PATH
        ]

class H2TPDataHeader:
    HEADER_NAMES = {
        HEADER_IDS.HOST: "Host",
        HEADER_IDS.PATH: "Path",
        HEADER_IDS.CLIENT_ID: "Client ID",
        HEADER_IDS.MIME_TYPE: "Mime Type",
        HEADER_IDS.STATUS: "Status"
    }

    def __init__(
        self,
        content: bytes,
        important: bool,
        hid: int
    ):
        self.content: bytes = content
        self.important: bool = important
        self.hid: int = hid

    def __str__(self) -> str:
        return f"0x{hex(self.hid)[2:].zfill(2)}/{self.hid_to_str()}{' (!)' if self.important else ''}"

    def hid_to_str(self) -> str:
        if self.hid in self.HEADER_NAMES:
            return self.HEADER_NAMES[self.hid]

        if self.hid < 0x80:
            return "Reserved"

        return "User-Defined"

class H2TPData:
    def __init__(
        self,
        version: tuple[int, int],
        was_corrupted: bool,
        headers: dict[int, tuple[bytes, bool]],
        body: bytes,
        checksum_valid: bool
    ):
        self.version: tuple[int, int] = version
        self.was_corrupted: bool = was_corrupted
        self.headers: dict[int, H2TPDataHeader] = {}
        self.body: bytes = body
        self.checksum_valid: bool = checksum_valid

        for hid, data in headers.items():
            self.headers[hid] = H2TPDataHeader(*data, hid)

    def __str__(self) -> str:
        return f"'{bytes.decode(self.body, errors='ignore')}' ({len(self.headers)} header{'s' if len(self.headers) != 1 else ''}: {', '.join([str(i) for i in self.headers.values()])})"

class BaseH2TPRequest:
    H2TP_HEADER = b"\xb0\x00\xb1\xe5H2TP"
    H2TP_VERSION = (0x00, 0x01)
    DEFAULT_CLIENT_ID = b"Python/h2tp"
    MAX_HEADER_LENGTH = 32_767
    MAX_BODY_LENGTH = 9_223_372_036_854_775_808
    CHECKSUM_XOR_VALUE = 0xb000b1e5

    def __init__(
        self,
        body: bytes | str | None,
        headers: dict[int, str | bytes | tuple[str | bytes, bool]] | None=None,
        compress: bool=False,
    ):
        self.body: bytes = str.encode(body) if isinstance(body, str) else (body or b"")
        self.use_compression: bool = compress
        self.corrupted: bool = False

        self.headers: dict[int, tuple[bytes, bool]] = {}

        # standardize header data
        if headers:
            for hid, data in headers.items():
                hid = clamp(0, hid, 255)

                if isinstance(data, tuple):
                    important = data[1]
                    content = data[0]

                else:
                    important = hid in HEADER_IDS.META.IMPORTANT_HEADERS
                    content = data

                if isinstance(content, str):
                    content = str.encode(content)
                else:
                    content = content

                self.headers[hid] = (content, important)

    @staticmethod
    def validate_checksum(data: bytes, checksum: bytes) -> bool:
        return BaseH2TPRequest.calculate_checksum(data) == checksum

    @staticmethod
    def calculate_checksum(data: bytes) -> bytes:
        checksum = 0xffffffff

        for i in data:
            checksum = checksum ^ (i << 24)

            for i in range(8):
                if checksum & 0x80000000:
                    checksum = (checksum & 0x7fffffff) << 1 ^ BaseH2TPRequest.CHECKSUM_XOR_VALUE
                else:
                    checksum = checksum << 1

        return b(checksum, 4)

    @staticmethod
    def compress(data: bytes) -> bytes:
        raise NotImplementedError("Compression hasn't been implemented")

    @staticmethod
    def parse(data: bytes, *, continue_parsing_corrupted: bool=False) -> H2TPData | None:
        if not data.startswith(BaseH2TPRequest.H2TP_HEADER):
            Log.warn("[H2TP] Invalid H2TP header")
            return None

        version = (
            data[len(BaseH2TPRequest.H2TP_HEADER)],
            data[len(BaseH2TPRequest.H2TP_HEADER) + 1]
        )

        checksum = data[len(BaseH2TPRequest.H2TP_HEADER) + 2 : len(BaseH2TPRequest.H2TP_HEADER) + 6]
        data = data[len(BaseH2TPRequest.H2TP_HEADER) + 6:]
        checksum_valid = BaseH2TPRequest.validate_checksum(data, checksum)

        if not checksum_valid:
            Log.warn("[H2TP] Invalid checksum")
            if not continue_parsing_corrupted:
                return None

        was_corrupted = data.startswith(b"CORR")
        if was_corrupted:
            data = data[4:]

        headers: dict[int, tuple[bytes, bool]] = {}
        if data.startswith(b"HEAD"):
            header_count = data[4]
            data = data[5:]

            for _ in range(header_count):
                header_length = (data[1] & 0x7f) << 8 | data[2]
                header_id = data[0]
                header_data = data[3:header_length + 3]

                headers[header_id] = (header_data, bool(data[1] & 0x80))
                data = data[3 + header_length:]

        # "BODY" header
        data = data[4:]

        compressed = bool(data[0] & 0x80)
        length = (data[0] & 0x7f) << 56 | data[1] << 48 | data[2] << 40 | data[3] << 32 | data[4] << 24 | data[5] << 16 | data[6] << 8 | data[7]
        body = data[8:length + 8]

        if compressed:
            raise NotImplementedError("Compression hasn't been implemented")

        return H2TPData(
            version,
            was_corrupted,
            headers,
            body,
            checksum_valid
        )

    @staticmethod
    def get_from_stream(socket: socket.socket) -> bytes:
        data = socket.recv(len(BaseH2TPRequest.H2TP_HEADER) + 2 + 4)

        while True:
            next_sect = socket.recv(4)
            data += next_sect
            if next_sect == b"HEAD":
                data += socket.recv(1)
                header_count = data[-1]

                for _ in range(header_count):
                    data += socket.recv(3)
                    header_length = (data[-2] & 0x7f) << 8 | data[-1]
                    data += socket.recv(header_length)

            elif next_sect == b"CORR":
                ...

            elif next_sect == b"BODY":
                data += socket.recv(8)
                body_length = (data[-8] & 0x7f) << 56 | data[-7] << 48 | data[-6] << 40 | data[-5] << 32 | data[-4] << 24 | data[-3] << 16 | data[-2] << 8 | data[-1]
                data += socket.recv(body_length)
                break

        f = open("test.bin", "wb")
        f.write(data)
        f.close()

        return data

    def build_request(self) -> bytes:
        header_data = b""
        if self.headers:
            header_data = b"HEAD" + b(clamp(0, len(self.headers), 255))

            for hid, data in self.headers.items():
                header_value = data[0][:self.MAX_HEADER_LENGTH]
                header_data += b(hid) + b(len(header_value) | (data[1] << 15), 2) + header_value

        body_value = (self.compress(self.body) if self.use_compression else self.body)[:self.MAX_BODY_LENGTH]
        data = header_data + b"BODY" + b(len(body_value) | (self.use_compression << 63), 8) + body_value

        if self.corrupted:
            data = b"CORR" + data

        return self.H2TP_HEADER + b(self.H2TP_VERSION[0] << 8 | self.H2TP_VERSION[1], 2) + self.calculate_checksum(data) + data
