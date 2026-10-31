`tls_connect(host, port, timeout_ms?, ca_file?)` opens a TCP connection and
performs a TLS handshake. It returns a `socket` whose methods mirror the TCP
ones.

```spark
var socket = tls_connect("example.com", 443, 5000);

socket.write("GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n");

var reply = socket.read(65536);
while (reply != nil) {
    print(reply);
    reply = socket.read(65536);
}
socket.close();
```

## Methods

| Call | Result |
| --- | --- |
| `sock.read(max)` | Up to `max` bytes, or `nil` at end of stream. |
| `sock.write(data)` | Writes all of `data`; returns the byte count. |
| `sock.close()` | Sends a best-effort `SSL_shutdown` and closes. |

TLS sockets reject `send`, `recv`, `recv_line`, `wait` and `net_select`, so
ciphertext can never be read as plaintext. Use `read` and `write`.

## Verification is always on

This is the most important property of the API: there is no option to skip
verification.

- The certificate chain is checked against the system trust store, or against
  `ca_file` when supplied.
- The host name (or IP address) must match the certificate.
- SNI is sent for DNS names.
- IPv4 and IPv6 literals are verified against the certificate's IP subject
  alternative names.
- TLS 1.2 is the minimum accepted version.
- Partial wildcards are rejected.
- Compression and server-initiated renegotiation are disabled.
- No public API can set `SSL_VERIFY_NONE`.

`ca_file` is a PEM file with one or more trusted certificates. It is useful for
a private CA and for tests.

```spark
var socket = tls_connect("internal.example", 8443, 5000, "/etc/ssl/private-ca.pem");
```

## Timeouts

`timeout_ms` bounds the connect, the handshake, every `read` and every `write`.
Omitted or `nil` waits forever. A negative value is an error.

```spark
var socket = tls_connect("example.com", 443, 10000);
```

The handshake and the reads/writes yield the coroutine like the TCP methods, so
a server with many TLS connections still shares one process.

## Errors

| Situation | Error |
| --- | --- |
| Self-signed certificate | `NetworkError: TLS certificate verification failed: ...` |
| Unknown issuer | `NetworkError: TLS certificate verification failed: ...` |
| Wrong host name | `NetworkError: TLS certificate verification failed: hostname mismatch` |
| Expired certificate | `NetworkError: TLS certificate verification failed: ...` |
| Deadline exceeded | `TimeoutError` |
| Unknown host / refused connection | `NetworkError` |
| Missing or unreadable CA file | Error naming the CA file |

```spark
try {
    var socket = tls_connect("expired.badssl.com", 443, 5000);
} catch (error) {
    print(error.type, error.message);
}
```

::: danger Do not expect a "disable verification" switch
It does not exist, by design. Programs cannot silently accept an untrusted
chain. For local development, generate a throwaway CA and pass it as
`ca_file`; for public certificates, fix the host name or the trust store.
:::

## HTTPS is built on this

`http_get("https://...")`, `http_post` and the other HTTP helpers use the same
handshake and verification rules. `http_request` exposes `ca_file` for private
CAs; the positional helpers always use the system store. See
[HTTP Client](@networking/http-client).

## A complete example

```spark
fn fetch_https(host, path) {
    var socket = tls_connect(host, 443, 10000);
    try {
        socket.write(
            "GET " + path + " HTTP/1.1\r\n" +
            "Host: " + host + "\r\n" +
            "Connection: close\r\n\r\n"
        );

        var response = "";
        var chunk = socket.read(65536);
        while (chunk != nil) {
            response += chunk;
            chunk = socket.read(65536);
        }
        return response;
    } finally {
        socket.close();
    }
}

print(fetch_https("example.com", "/"));
```

For production code, prefer the HTTP client, which handles framing,
`Content-Length`, chunked bodies and redirects. This example shows the raw
layer; in 0.1.0 the HTTP client is synchronous and blocks the process, while
the socket methods yield their coroutine.

## Limits

- `read(max)` returns at most 16 MiB.
- `write(data)` accepts at most `INT32_MAX` bytes.
- TLS 1.2 minimum; no TLS 1.0/1.1.
- Certificate chains are verified to depth 10.

See [Limits and Performance](@internals/limits-and-performance).

## Next

- [HTTP Client](@networking/http-client) — verification and `ca_file` in the HTTP API.
- [WebSockets](@networking/websockets) — `wss://` uses the same trust rules.
- [Sockets and Timeouts](@networking/sockets) — the underlying transport.