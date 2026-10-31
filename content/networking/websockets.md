`ws_connect(url, timeout_ms?, ca_file?)` opens an RFC 6455 WebSocket client over
`ws://` or `wss://`. The URL supplies the path and query; the upgrade handshake
is verified, and the result is a GC-managed `websocket` (`type()` reports
`"websocket"`).

```spark
var socket = ws_connect("wss://gateway.example/?v=10", 5000);

socket.send_text("hello");
var frame = socket.receive();      // {opcode: "text", data: "hello"}
print(frame.opcode, frame.data);

socket.close(1000, "done");
```

## API

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

## Text, binary and UTF-8

- `send_text` requires valid UTF-8.
- Received text and close reasons are validated as UTF-8.
- `send_binary` sends the bytes of a Spark string. Spark strings are text, so
  there is no separate byte type in 0.1.0; treat the payload as opaque bytes on
  the other side.

```spark
socket.send_binary("\x00\x01\x02");
```

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
the connection timeout. The TCP connect and the TLS handshake are synchronous
and bounded by `timeout_ms`, which also becomes the default deadline for
`receive`.

## wss:// verification

`wss://` uses the same chain and host-name verification as `tls_connect`.
`ca_file` injects a PEM trust store and is ignored by `ws://`. There is no way
to disable verification. See [TLS](@networking/tls).

## Errors

| Situation | Error |
| --- | --- |
| Handshake rejected (status, headers, accept digest) | `NetworkError` |
| Certificate or host-name failure | `NetworkError` |
| Deadline exceeded | `TimeoutError` |
| Frame or message over 16 MiB | `ValueError` on send, `NetworkError` on receive |
| Control payload over 125 bytes, close reason over 123 | `ValueError` |
| Invalid UTF-8 in `send_text` | `ValueError` |
| Protocol violation | `NetworkError` after a close with `1002`, `1007` or `1009` |

Protocol violations include masked server frames, reserved bits or opcodes, an
orphan continuation, a new data frame inside a fragmented message, invalid
UTF-8 and an invalid close code. The client sends a best-effort close frame and
closes the transport.

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

## No WebSocket server (yet)

0.1.0 ships a client only. A server-side frame writer needs a byte-buffer type,
which is planned as the `bytes` type in 0.2. The roadmap tracks this as the
blocker for a Spark WebSocket server. See
[Project Status and Roadmap](@appendix/roadmap).

## Next

- [TLS](@networking/tls) — the trust rules behind `wss://`.
- [HTTP Server](@networking/http-server) — the server library that does exist.
- [Example Gallery](@appendix/examples) — the full Discord client.