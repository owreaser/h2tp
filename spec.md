# h2tp
it's like http but if it was completely different

Current spec version: (hex) `00 01`

## Basic Format
Requests and responses both have the same general format for the body data, with
some minor exceptions. The default port for h2tp is `2`. Everything on h2tp is
in **big endian**.

```
h2tp signature.........  ver..  checksum...  headers...................  body header  len....................  body ...............
b0 00 b1 e5 48 32 54 50  vM vm  xx xx xx xx  48 45 41 44 Hc hi hl hl hd  42 4f 44 59  00 00 00 00 00 00 00 0d  48 65 6c 6c 6f 2c 20 77 6f 72 6c 64 21
```

- Every h2tp requests starts with the 8 bytes `b0 00 b1 e5 48 32 54 50` ("booobies"
  represented as hex, then the literal bytes for "H2TP")
- `vM`: Major version of the specification used
- `vm`: Minor version of the specification used
- The checksum is calculated somehow. I'll get to this eventually. It is calculated from everything after it, so headers, length, and body.
- The bytes `48 45 41 44` indicate the beginning of the headers section (the
  literal bytes for "HEAD"). This entire section can be omitted, if no headers
  are applicable. This should never happen for a client, however, because the
  host (`0x00`) and path (`0x01`) headers are necessary to properly communicate
  intent to the server, except for maybe extremely rare use cases.
- `Hc`: Number of headers - `hi`, `hl`, and `hd` repeat this many times for each
  header.
- `hi`: Header ID (`0x00-0x7f` are reserved, `0x80-0xff` are for user-defined
  headers)
- `hl`: Length of a header - If the first bit of the length is set to `1`, that
  indicates that this header is an important header, and if the server doesn't
  recognize it, an error should be thrown. Length can be between `0x0000-0x7fff`
  (0-32,767 bytes).
- `hd`: The actual data for the header.
- The body section starts with the raw bytes "BODY".
- The length is 8 bytes, with the very first bit indicating wheither or not the
  stream is compressed using `zstd` compression. If it is compressed, the length
  will correspond to the compressed length, not the original length. The body
  has a max size of 8 PiB (9,223,372,036,854,775,808 bytes), after compression.

| Header ID | Name | Description | Example Value | HTTP Header Equivalent | Important? |
|-----------|------|-------------|---------------|------------------------|------------|
| 0x00 | Domain | The domain of the website you're accessing. | `google.com` | `Host` | Yes |
| 0x01 | Path | The path of the website you're accessing. | `/api/abcdefg` | *None* | Yes |
| 0x02 | Client ID | Information about the client. | `Python/h2tp` | `User-Agent` | No |
| 0x03 | Mime Type | The mime type of the body of the request. | `text/html` | `Content-Type` | No |
| 0x04 | Status | The success status of the request.. | 200 OK | HTTP Status Codes | No |
| 0x05-0x79 | Reserved | These are reserved for future use. | *None* | *None* | No |
| 0x80-0xff | User-Defined Headers | These can be used for any purpose by the user. | Any | `X-...` | No |

## Behavior with a Failed Checksum
If a checksum isn't matched properly, the server or client can discard the
request entirely. Optionally, the client should re-request the server if the
server indicates that a checksum has failed. If the response from the server
was corrupted, the client can optionally re-request the server, with the caveat
that the server would process the request twice.

If the data sent to the server is inconsequential, then the server or client can
also continue on as if nothing happened.

With a failed checksum, a server would respond with the normal format, however
with the raw bytes "CORR" added before the header section begins. The request
can continue with the standard format if it can still be properly processed, or
the rest of the request can be discarded and returned as it is. No headers need
to be sent, however the eight length bytes do need to be sent.

The "CORR" bytes should be included when calculating the checksum.
