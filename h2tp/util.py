from typing import TypeVar
from urllib.parse import unquote as url_decode

T = TypeVar("T", bound="int | float")

class Log:
    LOG_LEVEL_DEBUG = 0
    LOG_LEVEL_INFO = 1
    LOG_LEVEL_WARNING = 2
    LOG_LEVEL_ERROR = 3
    LOG_LEVEL_NONE = 4

    @staticmethod
    def debug(*args):
        if LOG_LEVEL <= Log.LOG_LEVEL_DEBUG:
            print(*args)

    @staticmethod
    def info(*args):
        if LOG_LEVEL <= Log.LOG_LEVEL_INFO:
            print(*args)

    @staticmethod
    def warn(*args):
        if LOG_LEVEL <= Log.LOG_LEVEL_WARNING:
            print("\x1b[33m", end="")
            print(*args, end="")
            print("\x1b[0m")

    @staticmethod
    def err(*args):
        if LOG_LEVEL <= Log.LOG_LEVEL_ERROR:
            print("\x1b[31m", end="")
            print(*args, end="")
            print("\x1b[0m")

LOG_LEVEL = Log.LOG_LEVEL_INFO

if LOG_LEVEL <= Log.LOG_LEVEL_DEBUG:
    Log.debug("Debug")
    Log.info("Info")
    Log.warn("Warn")
    Log.err("Error")

def clamp(mini: T | None=None, val: T=0, maxi: T | None=None) -> T:
    return max(mini or val, min(maxi or val, val))

def b(i: int, length: int=1) -> bytes:
    # converts an int to bytes of a certain length
    return i.to_bytes(length=length, byteorder="big")

def normalize_path(path: str) -> str:
    return url_decode(path.split("?")[0].split("#")[0])
