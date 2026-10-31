Spark ships TCP and UDP sockets as part of the language, with timeouts, name
resolution over IPv4 and IPv6, and a scheduler that suspends the calling
coroutine instead of blocking the process.

## The resource model

Sockets and servers are GC-managed objects:

- Each owns a file descriptor.
- `close()` releases it immediately.
- The collector's finalizer closes it when it becomes unreachable.
- A shutdown closes anything left.
- Using a closed handle is a runtime error.
- `type()` reports `"socket"` or `"server"`.

```spark
var socket = tcp_connect("example.com", 80);
print(type(socket));      // socket
socket.close();
```

## Creating sockets

| Call | Result |
| --- | --- |
| `tcp_connect(host, port, timeout_ms?)` | Connected TCP client socket. |
| `tcp_listen(host, port, backlog?)` | Listening server; port `0` binds an ephemeral port. |
| `udp_bind(host, port, timeout_ms?)` | Bound UDP socket for datagrams. |
| `tls_connect(host, port, timeout_ms?, ca_file?)` | TLS client; see [TLS](@networking/tls). |
| `net_hostname()` | Local host name. |

`host` may be a name, an IPv4 literal, or an IPv6 literal in brackets:

```spark
tcp_connect("localhost", 8080);
tcp_connect("127.0.0.1", 8080);
tcp_connect("[::1]", 8080);
```

`getaddrinfo` resolves names, and every resolved address is tried in turn, so
`localhost` works over either family. `port` must be in `0..65535`.

## Timeouts

Every operation accepts a millisecond timeout:

```spark
var socket = tcp_connect("example.com", 80, 5000);   // 5 second deadline
```

- The timeout passed to `tcp_connect` / `udp_bind` becomes the socket's default
  deadline and bounds its later reads and writes.
- An accepted socket inherits the `accept` timeout.
- Omitted or `nil` means "wait forever"; a negative value is an error.

Always pass a timeout for operations driven by untrusted input or by a peer
that may idle.

## TCP client methods

| Call | Result |
| --- | --- |
| `sock.send(data)` | Writes all of `data`; returns the byte count. |
| `sock.recv(max)` | Up to `max` bytes, or `nil` at end of stream. |
| `sock.recv_line(max?)` | Up to the next newline; `nil` at end of stream. Default bound 64 KiB. |
| `sock.wait(read?, write?, timeout_ms?)` | Waits for readability/writability; `true` when ready, `TimeoutError` on the deadline. |
| `sock.peer()` / `sock.local()` | `{host, port}` map with the numeric peer / local address. |
| `sock.close()` | Closes the socket. |

```spark
var socket = tcp_connect("example.com", 80, 5000);
socket.send("GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n");

while (true) {
    var chunk = socket.recv(4096);
    if (chunk == nil) {
        break;
    }
    print(chunk);
}
socket.close();
```

`recv_line` drops the newline and a preceding `\r`. It keeps an internal read
buffer, so it never consumes bytes past the line it returns; a later `recv`
drains that buffer first.

`recv` and `recv_line` accept at most 16 MiB. Larger values raise `ValueError`.

## TCP servers

| Call | Result |
| --- | --- |
| `srv.accept(timeout_ms?)` | An accepted socket, or `nil` on timeout. |
| `srv.port()` | The bound port. |
| `srv.close()` | Closes the listener. |

```spark
var server = tcp_listen("127.0.0.1", 0);
print("listening on", server.port());

var client = server.accept(5000);
if (client != nil) {
    client.send("hello\n");
    client.close();
}
server.close();
```

`accept` returning `nil` on a timeout is the one place a timeout is not an
exception, so a server loop can poll and check a shutdown flag.

## UDP

| Call | Result |
| --- | --- |
| `sock.send_to(data, host, port)` | Sends one datagram; returns the byte count. |
| `sock.recv_from(max)` | `{data, host, port}` for one datagram. |

```spark
var socket = udp_bind("127.0.0.1", 0, 2000);

socket.send_to("ping", "127.0.0.1", 9999);

var message = socket.recv_from(1024);
if (message != nil) {
    print(message.data, message.host, message.port);
}
```

A UDP socket uses `send_to` and `recv_from`; the stream methods (`send`,
`recv`, `recv_line`) belong to TCP sockets.

## Multiplexing with net_select

`net_select(readables, timeout_ms?)` waits until any socket in the array is
readable and returns the array of ready **indexes**. An empty array means the
timeout expired.

```spark
var sockets = [client_a, client_b];
var ready = net_select(sockets, 1000);
if (len(ready) > 0) {
    var socket = sockets[ready[0]];
    var data = socket.recv(1024);
}
```

This is useful when you manage descriptors yourself rather than spawning one
coroutine per connection.

## The scheduler

Blocking socket operations **yield the coroutine**, not the process. A call
that would block registers a wait on its descriptor; the scheduler polls the
registered sockets, sleeping until the nearest deadline, and wakes the
coroutine when the descriptor is ready or the deadline passes.

`tcp_connect`, `accept`, `recv`, `recv_line`, `send`, TLS handshakes and
WebSocket receives all participate. One process serves many connections:

```spark
fn echo(client) {
    while (true) {
        var line = client.recv_line();
        if (line == nil) {
            break;
        }
        client.send(line + "\n");
    }
    client.close();
}

var server = tcp_listen("127.0.0.1", 0);
print("port", server.port());

while (true) {
    var client = server.accept(1000);
    if (client != nil) {
        spawn(echo, client);
    }
}
```

This is the pattern behind `examples/echo_server.spark`. Run it and connect
with `nc`:

```bash
spark examples/echo_server.spark 0
```

```bash
printf 'hello\n' | nc 127.0.0.1 <port>
```

::: warning Callbacks and modules cannot suspend
A would-block socket call inside a native callback (`map`, `each`, `sort_by`,
...) or during an imported module's load raises `RuntimeError` instead of
suspending, because those run at a deeper `run_depth`. Do the I/O in the
coroutine body.
:::

## Errors

| Error | When |
| --- | --- |
| `NetworkError` | Unknown host, refused connection, invalid port, reset connection, descriptor exhaustion. |
| `TimeoutError` | An operation exceeded its deadline. |
| `ValueError` | Invalid arguments (negative timeout, oversized buffer, bad address). |

`accept` returns `nil` on timeout rather than raising. Descriptor exhaustion is
reported as `NetworkError: too many open descriptors`, not a crash.

```spark
try {
    var socket = tcp_connect("no-such-host.invalid", 80, 1000);
} catch (error) {
    print(error.type);      // NetworkError
    print(error.message);
}
```

Network error messages redact URL userinfo and never echo headers or bodies.
See [HTTP Client](@networking/http-client) for the HTTP-specific limits.

## Security notes

- Spark is not a sandbox and imposes no destination allow-list. A program that
  accepts URLs from untrusted input must validate schemes, hosts and address
  ranges itself. See [HTTP Client](@networking/http-client#security).
- Timeouts are the difference between a robust service and one that hangs. Pass
  them explicitly.
- Descriptors are capped by the process limit (`RLIMIT_NOFILE`). Embedders
  should set a limit and handle the resulting `NetworkError`.

## Limits

- `recv` / `recv_from`: at most 16 MiB.
- `recv_line`: at most 16 MiB; default 64 KiB.
- Ports: `0..65535`.
- Values waiting in a channel: 16,777,216.

See [Limits and Performance](@internals/limits-and-performance).

## Next

- [TLS](@networking/tls) — encrypted sockets with mandatory verification.
- [HTTP Client](@networking/http-client) — a ready-made HTTP/1.1 client.
- [HTTP Server](@networking/http-server) — a server library written in Spark.
- [WebSockets](@networking/websockets) — RFC 6455 clients.