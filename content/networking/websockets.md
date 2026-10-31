Spark speaks RFC 6455 in both directions. `ws_connect(url, timeout_ms?, ca_file?)`
opens a client over `ws://` or `wss://`; `ws_accept(socket, timeout_ms?)` upgrades
a socket returned by `tcp_listen(...).accept()` into a server connection. Both
return the same GC-managed `websocket` object (`type()` reports `"websocket"`),
so the framing, message and close rules below apply to either side.

```spark
var socket = ws_connect("wss://gateway.example/?v=10", 5000);

socket.send_text("hello");
var frame = socket.receive();      // {opcode: "text", data: "hello"}
print(frame.opcode, frame.data);

socket.close(1000, "done");
```

## Client API

| Call | Result |
| --- | --- |
| `ws.send_text(data)` | Sends one masked text message; returns the byte count. |
| `ws.send_binary(data)` | Sends one masked binary message; returns the byte count. |
| `ws.receive(timeout_ms?)` | Next `{opcode, data}` message, or `nil` when closed. |
| `ws.ping(data?)` | Sends a ping; returns the payload byte count. |
| `ws.close(code?, reason?)` | Starts the close handshake; default code `1000`. |

```spark
var socket = ws_connect("ws://127.0.0.1:9001/chat?room=general", 3000);

socket.send_text("hello");
print(socket.receive().data);

socket.ping("keepalive");
print(socket.receive().opcode);    // pong

socket.close(1000, "bye");
print(socket.receive());           // nil once the peer closes
```

The URL supplies the path and query, and the upgrade handshake is verified:
status `101`, `Upgrade: websocket`, `Connection: Upgrade` and the
`Sec-WebSocket-Accept` digest. A server that selects an extension or a
subprotocol the client did not request fails the handshake.

## WebSocket server

`ws_accept(socket, timeout_ms?)` performs the server half of the handshake on a
socket accepted from `tcp_listen`:

```spark
var server = tcp_listen("127.0.0.1", 8080);

while (true) {
    var transport = server.accept();
    var ws = ws_accept(transport, 5000);

    while (true) {
        var frame = ws.receive();

        if (frame == nil) {
            break;
        }
        if (frame.opcode == "text") {
            ws.send_text("echo: " + frame.data);
        }
    }
}
```

The socket must be an open plain TCP socket, and `ws_accept` must be the first
read on it: the opening request is consumed by the handshake, and any bytes the
peer sent after it move into the receive buffer. The returned `websocket` owns
the socket; do not use the socket object again.

The handshake checks the request line (`GET`, `HTTP/1.1`, an origin-form target)
and the upgrade headers (`Upgrade`, `Connection`, `Sec-WebSocket-Version: 13`
and a `Sec-WebSocket-Key` encoding 16 bytes), then answers `101 Switching
Protocols` with the matching `Sec-WebSocket-Accept`. Extensions and
subprotocols are ignored, never selected.

- A request that is not a valid upgrade is answered with `400 Bad Request`, the
  transport is closed and `NetworkError` is raised. A read failure keeps its
  type, so a stalled handshake raises `TimeoutError`.
- The handshake is synchronous and bounded by `timeout_ms`, like the HTTP
  client: it blocks the process rather than yielding its coroutine. Run a server
  that must stay responsive in its own process.
- Server frames are sent **unmasked**, and incoming client frames **must be
  masked**. An unmasked client frame is a protocol error: the server sends a
  close frame with `1002` and raises `NetworkError`, mirroring the client's
  rejection of masked server frames.

The server supports the same methods as the client (`send_text`, `send_binary`,
`receive`, `ping`, `close`) with the same message and close semantics.

```spark
var server = tcp_listen("127.0.0.1", 0);
print("ws://127.0.0.1:" + str(server.port()) + "/");

var transport = server.accept(5000);
var ws = ws_accept(transport, 5000);

ws.send_text("welcome");
print(ws.receive().data);
ws.close(1000, "done");
```

## Messages

`receive` returns a map with:

| Key | Values |
| --- | --- |
| `opcode` | `"text"`, `"binary"` or `"pong"`. |
| `data` | The message payload as a string. |

- Fragmented messages are reassembled before they are returned.
- A ping from the peer is answered automatically with a pong carrying the same
  payload, and is **not** returned to the program.
- An unsolicited pong is returned as an `"pong"` message.
- Control frames may arrive between the fragments of a message.
- `nil` means the peer closed the connection, the close handshake completed, or
  a previous `close` already closed it.

## Text, binary and bytes

- `send_text` requires valid UTF-8; `send_binary` does not. Both take a Spark
  string and send its bytes unchanged (a client masks the frame, a server does
  not).
- Received text and close reasons are validated as UTF-8; binary payloads are
  not.
- `receive` returns the payload as a string. For a binary frame that string
  holds the raw bytes, so `bytes_from(frame.data)` recovers them exactly and
  `bytes_to_array` shows the values.

```spark
var frame = socket.receive();

if (frame.opcode == "binary") {
    print(bytes_to_array(bytes_from(frame.data)));   // for example [255, 0, 65]
}
```

The WebSocket methods take strings, not `bytes`, and there is no implicit
conversion between the two types: use `to_string(bytes)` (which requires valid
UTF-8) to build a payload from a `bytes` value, and `bytes_from(text)` or
`bytes_from(frame.data)` in the other direction. See
[Types and Values](@guide/types-and-values) for the byte type and its codecs.

## Timeouts and the scheduler

`receive` yields the coroutine while it waits for bytes. It accepts a per-call
timeout, which is what makes a heartbeat loop possible:

```spark
var socket = ws_connect("wss://gateway.example/", 5000);

while (true) {
    try {
        var frame = socket.receive(1000);
        if (frame == nil) {
            break;
        }
        print(frame.opcode, frame.data);
    } catch (error) {
        if (error.type == "TimeoutError") {
            socket.ping("keepalive");
            continue;
        }
        throw error;
    }
}
```

`send_text`, `send_binary`, `ping` and `close` write synchronously, bounded by
the connection timeout. On the client, the TCP connect and the TLS handshake are
synchronous and bounded by `timeout_ms`, which also becomes the default deadline
for `receive`. On the server, `ws_accept` itself is the synchronous step; the
timeout it receives is the handshake deadline and the default deadline for
subsequent sends.

## wss:// verification

`wss://` uses the same chain and host-name verification as `tls_connect`.
`ca_file` injects a PEM trust store and is ignored by `ws://`. There is no way
to disable verification. See [TLS](@networking/tls). Server-side TLS is not
part of `ws_accept`: it takes a plain TCP socket.

## Errors

| Situation | Error |
| --- | --- |
| Handshake rejected (status, headers, accept digest) | `NetworkError` |
| Server handshake rejected (request line, headers, key) | `NetworkError` after `400` |
| Certificate or host-name failure | `NetworkError` |
| Deadline exceeded | `TimeoutError` |
| Frame or message over 16 MiB | `ValueError` on send, `NetworkError` on receive |
| Control payload over 125 bytes, close reason over 123 | `ValueError` |
| Invalid UTF-8 in `send_text` | `ValueError` |
| Protocol violation | `NetworkError` after a close with `1002`, `1007` or `1009` |

Protocol violations include masked server frames (client side), unmasked client
frames (server side), reserved bits or opcodes, an orphan continuation, a new
data frame inside a fragmented message, invalid UTF-8 and an invalid close code.
The failing side sends a best-effort close frame and closes the transport.

Valid close codes accepted from a peer are `1000`–`1014` except the reserved
`1004`, `1005`, `1006` and `1015`, plus the application range `3000`–`4999`.

## Limits

| Limit | Value |
| --- | --- |
| One frame | 16 MiB |
| One assembled message | 16 MiB |
| Control payload | 125 bytes |
| Close reason | 123 bytes |
| Disconnect timeout | caller-supplied |

The limits are identical in both directions: the server reuses the client's
framing and validation code.

## The echo server and client examples

`examples/ws_echo_server.spark` and `examples/ws_echo_client.spark` are a
matching pair; the test suite runs them against each other.

```bash
# terminal 1
spark examples/ws_echo_server.spark 0

# terminal 2 — use the port the server printed
spark examples/ws_echo_client.spark ws://127.0.0.1:PORT/
```

The client prints:

```text
echo: text hello from spark
closed: nil
```

The server echoes every text or binary message until the client closes, then
prints `closed` for the connection and accepts the next one.

## The Discord gateway example

`examples/discord_bot.spark` is a small Discord-shaped gateway client. It reads
`DISCORD_TOKEN` from the environment (and never prints it), connects to
`DISCORD_GATEWAY_URL` or the real gateway, waits for `HELLO`, sends
`IDENTIFY`, heartbeats at the interval from `HELLO` and answers a
`MESSAGE_CREATE` whose content is `ping` with `pong`.

1. Build Spark with `make`.
2. Start the offline mock gateway in one terminal:

   ```bash
   python3 tests/run_tests.py --mock-gateway
   ```

   It prints a `ws://127.0.0.1:PORT/?v=10` URL and keeps running.

3. In another terminal, run the example against it:

   ```bash
   DISCORD_TOKEN=test-token \
   DISCORD_GATEWAY_URL="ws://127.0.0.1:PORT/?v=10" \
   spark examples/discord_bot.spark
   ```

   Expected output:

   ```text
   ready
   message: ping
   reply sent
   closed
   ```

4. For the real gateway, export a bot token and omit `DISCORD_GATEWAY_URL`:

   ```bash
   DISCORD_TOKEN=... spark examples/discord_bot.spark
   ```

The test suite starts the same mock gateway on an ephemeral port, so the
example is exercised on every run without contacting Discord.

A condensed heartbeat loop:

```spark
var sequence = nil;
var heartbeat_ms = 1000;

while (true) {
    var frame = nil;
    try {
        frame = socket.receive(heartbeat_ms);
    } catch (error) {
        if (error.type == "TimeoutError") {
            socket.send_text(to_json({"op": 1, "d": sequence}));
            continue;
        }
        throw error;
    }

    if (frame == nil) {
        break;
    }
    if (frame.opcode == "text") {
        var event = from_json(frame.data);
        if (event["s"] != nil) {
            sequence = event["s"];
        }
        print(event["op"]);
    }
}
```

## Next

- [TLS](@networking/tls) — the trust rules behind `wss://`.
- [HTTP Server](@networking/http-server) — the server library for plain HTTP.
- [Example Gallery](@appendix/examples) — the full Discord client and the echo pair.