Spark includes an HTTP/1.1 client. It handles `Content-Length`, chunked bodies,
read-to-EOF bodies, redirects, TLS and explicit resource limits.

```spark
var response = http_get("https://example.com/");

print(response.status);              // 200
print(response.headers["content-type"]);
print(response.body);
```

## API

| Call | Result |
| --- | --- |
| `http_get(url, body?, headers?, timeout_ms?, follow_redirects?, max_body?)` | `{status, headers, body}` |
| `http_post(...)` | Same, with `POST`. |
| `http_put(...)` | Same, with `PUT`. |
| `http_delete(...)` | Same, with `DELETE`. |
| `http_request(options)` | Same, driven by a map. |

The positional helpers take the same six arguments in the same order. The
`body` is a string, `headers` is a map, and the last three control the
deadline, redirect behavior and body cap.

```spark
var created = http_post(
    "http://api.local/items",
    "{\"name\": \"x\"}",
    {"Content-Type": "application/json"},
    5000
);
print(created.status);    // 201
```

## The response map

| Key | Type | Meaning |
| --- | --- | --- |
| `status` | int | HTTP status code. |
| `headers` | map | Header names lowercased; a repeated header keeps its last value. |
| `body` | string | The whole body. |

```spark
print(response.headers["server"]);
print(response.headers["content-type"]);
```

Header names are lowercased on the way in, so always look them up lowercase.

## Options for http_request

`http_request` accepts exactly these keys; unknown keys are rejected.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `url` | string | required | Absolute `http://` or `https://` URL. |
| `method` | string | `"GET"` | Request method. |
| `body` | string | none | Request body. |
| `headers` | map | `{}` | Request headers. |
| `timeout_ms` | int | `30000` | Whole-request deadline, including redirects. |
| `follow_redirects` | bool | `true` | Whether to follow redirects. |
| `max_body` | int | `16777216` | Body cap; may not exceed 16 MiB. |
| `ca_file` | string | system store | PEM trust store for `https://`. |

```spark
var response = http_request({
    "url": "https://api.example.com/v1/ping",
    "method": "POST",
    "body": "{\"ping\": true}",
    "headers": {"Content-Type": "application/json"},
    "timeout_ms": 8000,
    "follow_redirects": true,
    "max_body": 1048576,
});
```

`ca_file` is the only way to use a private CA with the HTTP client; the
positional helpers always use the system trust store.

## Redirects

`301`, `302`, `303`, `307` and `308` are followed by default, up to five hops.

- `303`, and `301`/`302` after a `POST`, switch to `GET` and drop the body.
- A relative `Location` header is resolved against the request URL.
- A redirect loop or a sixth hop raises `NetworkError`.

```spark
var response = http_get("http://example.com/old", nil, nil, 5000, false);
print(response.status);   // 301, not followed
```

## Limits

| Limit | Value | Failure |
| --- | --- | --- |
| Status line + headers | 64 KiB | `NetworkError` |
| Headers | 1000 | `NetworkError` |
| Redirects | 5 | `NetworkError` |
| Body | 16 MiB default (`max_body`) | `NetworkError` |
| Whole request | 30 s default (`timeout_ms`) | `TimeoutError` |

A value of `0` for `timeout_ms` also means "use the default", not "wait
forever". The HTTP client is bounded by design.

## HTTPS

`https://` performs the same chain and host-name verification as
`tls_connect`, with no way to disable it:

```spark
var response = http_get("https://example.com/", nil, nil, 10000);
```

A verification failure raises `NetworkError`; a deadline raises
`TimeoutError`. See [TLS](@networking/tls).

## Errors

| Situation | Error |
| --- | --- |
| Unknown host, refused connection | `NetworkError` |
| Malformed status line, premature EOF | `NetworkError` |
| Header, body or redirect limit exceeded | `NetworkError` |
| Deadline exceeded | `TimeoutError` |
| Newline in a URL or header value | `ValueError` |
| Unknown option key | `Error` naming the key |

A header value or URL containing a newline is rejected so a request cannot be
split into extra headers.

## URL helpers

| Call | Result |
| --- | --- |
| `url_parse(url)` | `{scheme, host, port, path, query, fragment}` |
| `url_encode(text)` | Percent-encodes form data; a space becomes `+`. |
| `url_decode(text)` | Inverse of `url_encode`; `ValueError` on a bad escape. |
| `parse_query(query)` | Map from key to array of values. |

```spark
var u = url_parse("http://user@[::1]:8080/a/b?x=1#top");
print(u.scheme);     // http
print(u.host);       // [::1]  (IPv6 literals keep their brackets)
print(u.port);       // 8080 (or the scheme default)
print(u.path);       // /a/b (defaults to "/")
print(u.query);      // x=1
print(u.fragment);   // top

print(url_encode("a b&c"));    // a+b%26c
print(url_decode("a+b%26c"));  // a b&c
print(parse_query("a=1&a=2&b="));
// {"a": ["1", "2"], "b": [""]}
```

- `port` is `nil` when the URL has no port and the scheme has no default.
- `host` is everything after an optional `userinfo@`; the userinfo is ignored.
- `url_parse` accepts a leading `?` in a query and skips empty pairs in
  `parse_query`.
- A malformed URL or escape raises `ValueError` instead of returning a partial
  result.

## A complete example

```spark
fn fetch_json(url) {
    var response = http_get(url, nil, {"Accept": "application/json"}, 10000);
    if (response.status != 200) {
        throw {
            "type": "HttpError",
            "message": "status ${response.status} from ${url}",
        };
    }
    return from_json(response.body);
}

var data = fetch_json("https://api.example.com/status");
print(data.status);
```

`examples/http_client.spark` is a runnable version that takes the URL from
`argv` and prints the status, headers and body.

## Synchronous by design (for now)

The HTTP client is a native that performs several steps (connect, handshake,
send, read, follow redirects) and cannot suspend halfway through. It therefore
**blocks the process** inside `poll(2)`, bounded by `timeout_ms`, instead of
yielding its coroutine.

This differs from raw sockets, which do yield. Consequences:

- A slow HTTP request stalls every coroutine for up to the deadline.
- Use the socket API if you need concurrent HTTP clients in one process.
- The roadmap calls for making the HTTP client coroutine-aware.

## Security

- There is no destination allow-list. A program that accepts URLs from
  untrusted input must validate schemes and reject loopback, link-local and
  private address ranges as appropriate.
- Error messages redact URL userinfo (`https://***@host/`) and never echo
  header values or bodies, so tokens do not leak through exceptions.
- Pass an explicit timeout for anything driven by untrusted input.
- TLS authenticates the peer; it does not make an arbitrary destination safe.

Embedders should enforce egress policy outside the language runtime. See
[Sockets and Timeouts](@networking/sockets#security-notes).

## Next

- [HTTP Server](@networking/http-server) — serving HTTP in pure Spark.
- [TLS](@networking/tls) — the verification rules behind `https://`.
- [Files, System and Data](@stdlib/files-and-system#json) — JSON encode/decode.