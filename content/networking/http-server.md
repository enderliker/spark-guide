Spark does not need native server code to speak HTTP: `lib/http.spark` builds an
HTTP/1.1 server on top of the socket layer, in pure Spark.

```spark
import "./lib/http";

fn handle(request) {
    return {"status": 200, "body": "hello ${request.path}\n"};
}

var server = tcp_listen("127.0.0.1", 8080);
http_serve(server, handle);
```

```bash
spark examples/http_server.spark
curl http://127.0.0.1:8080/
```

## API

`http_serve(server, handler, max_requests?)` accepts connections, reads one
request, calls `handler(request)` and writes the response. Without
`max_requests` it serves forever; with a number it stops after that many
accepted connections.

```spark
http_serve(server, handler, 10);   // serve ten connections, then return
```

## The request map

The handler receives:

| Key | Meaning |
| --- | --- |
| `method` | Request method (`GET`, `POST`, ...). |
| `target` | The raw request target, including the query. |
| `path` | The part before `?`. |
| `query` | The part after `?`, or `""`. |
| `version` | HTTP version from the request line. |
| `headers` | Map with lowercased header names. |
| `body` | Body read up to `Content-Length`. |

```spark
fn handle(request) {
    if (request.method != "GET") {
        return {"status": 405, "body": "method not allowed\n"};
    }

    var name = request.headers["x-name"] ?? "world";
    return {
        "status": 200,
        "headers": {"Content-Type": "text/plain; charset=utf-8"},
        "body": "hello ${name}\n",
    };
}
```

Query parameters are not parsed for you; use `parse_query` from the standard
library:

```spark
import "./lib/http";

fn handle(request) {
    var params = parse_query(request.query);
    var page = get(params, "page", ["1"])[0];
    return {"status": 200, "body": "page ${page}\n"};
}
```

## The response map

| Key | Default | Meaning |
| --- | --- | --- |
| `status` | `200` | Status code. |
| `headers` | `{}` | Response headers. |
| `body` | `""` | Response body. |

The library adds `Content-Type: text/plain; charset=utf-8` when the handler did
not provide one, computes `Content-Length`, skips a handler-supplied
`Content-Length`, and sends `Connection: close`.

```spark
return {
    "status": 201,
    "headers": {"Content-Type": "application/json"},
    "body": to_json({"created": true}),
};
```

## Routing

The library has no router; a handler is just a function. A practical pattern:

```spark
fn route(request) {
    switch (request.path) {
        case "/":
            return {"status": 200, "body": "home\n"};
        case "/health":
            return {"status": 200, "body": "ok\n"};
        case "/echo":
            return {"status": 200, "body": request.body};
        default:
            return {"status": 404, "body": "not found\n"};
    }
}
```

For path parameters, split the path and match segments:

```spark
fn user_id(path) {
    var parts = split(path, "/");
    if (len(parts) == 3 and parts[1] == "users") {
        return parts[2];
    }
    return nil;
}
```

## Errors

A parsing failure or an exception in the handler is caught by `http_serve`,
which answers `500` and closes the connection:

```spark
fn handle(request) {
    var data = from_json(request.body);   // may throw
    return {"status": 200, "body": str(len(data))};
}
```

```text
HTTP/1.1 500 Internal Server Error
Content-Length: 13
Content-Type: text/plain; charset=utf-8
Connection: close

server error
```

Log the error yourself if you need visibility; the default response is
deliberately generic.

## Limits

| Limit | Value |
| --- | --- |
| Request line | 8192 characters |
| Each header line | 8192 characters |
| Headers | 100 |
| Body | up to `Content-Length` |
| Connections | one at a time |

::: warning Text server, not a byte server
Spark strings are UTF-8 text and `Content-Length` is a byte count. The library
compares it to a character count, which matches only for ASCII bodies. Binary
requests and responses are unsupported. A `bytes` type is planned; see the
[roadmap](@appendix/roadmap).
:::

## Concurrency

`http_serve` accepts and serves **one connection at a time**. Each connection is
handled to completion before the next `accept`. This is simple and adequate for
local tools, tests and low-traffic endpoints.

For concurrency, accept in your own loop and `spawn` a handler per connection.
The library's request parser is not exported, so you would read and parse the
request yourself, or run several server processes behind a proxy. A
coroutine-aware `http_serve` is a natural extension but is not part of 0.1.0.

## TLS

The library serves plain HTTP only. TLS server-side support is not part of the
language (OpenSSL is used for the client transport). Put a reverse proxy in
front when you need HTTPS.

## A complete server

```spark
import "./lib/http";

fn handle(request) {
    switch (request.path) {
        case "/":
            return {"status": 200, "body": "Spark HTTP server\n"};
        case "/time":
            return {"status": 200, "body": str(time()) + "\n"};
        case "/echo":
            return {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": to_json({
                    "method": request.method,
                    "path": request.path,
                    "query": request.query,
                    "body": request.body,
                }),
            };
        default:
            return {"status": 404, "body": "not found\n"};
    }
}

var port = len(argv) > 1 ? int(argv[1]) : 8080;
var server = tcp_listen("127.0.0.1", port);
print("serving on http://127.0.0.1:${server.port()}/");
http_serve(server, handle);
server.close();
```

`examples/http_server.spark` is the shorter version from the repository. The
test suite drives it with Spark's own HTTP client (in a separate process) and
with a scripted Python client, so both ends are exercised offline.

## Next

- [HTTP Client](@networking/http-client) — the matching client.
- [WebSockets](@networking/websockets) — the other client protocol in 0.1.0.
- [Modules](@guide/modules) — how `import "./lib/http"` works.