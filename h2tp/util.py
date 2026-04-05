from typing import TypeVar
from urllib.parse import unquote as url_decode

T = TypeVar("T", bound="int | float")

def clamp(mini: T | None=None, val: T=0, maxi: T | None=None) -> T:
    return max(mini or val, min(maxi or val, val))

def b(i: int, length: int=1) -> bytes:
    # converts an int to bytes of a certain length
    return i.to_bytes(length=length, byteorder="big")

def normalize_path(path: str) -> str:
    return url_decode(path.split("?")[0].split("#")[0])
