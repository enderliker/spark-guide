Every example in the repository is runnable. This page collects the small ones
in full, with their output, and gives the commands for the rest.

| Example | Shows |
| --- | --- |
| `examples/hello.spark` | Printing and comments. |
| `examples/fibonacci.spark` | Recursion, loops, string building, iteration. |
| `examples/collections.spark` | Maps, `for-in`, string indexing, math. |
| `examples/closures.spark` | Memoization, captures, counters. |
| `examples/sorting.spark` | Bubble sort, median, `assert`. |
| `examples/echo_server.spark` | TCP server, coroutines. |
| `examples/http_server.spark` | `lib/http.spark` server. |
| `examples/http_client.spark` | HTTP client and `argv`. |
| `examples/ws_echo_server.spark` | WebSocket server with `ws_accept`. |
| `examples/ws_echo_client.spark` | WebSocket client matching the server. |
| `examples/regex_tokenizer.spark` | Regular expressions, capture groups and offsets. |
| `examples/discord_bot.spark` | WebSocket gateway client. |

## Hello

```spark
// First program in Spark.
print("Hello, Spark!");
print("This language compiles to bytecode and runs on a virtual machine written in C.");
```

```bash
spark examples/hello.spark
```

```text
Hello, Spark!
This language compiles to bytecode and runs on a virtual machine written in C.
```

## Fibonacci

```spark
fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

for (var i = 0; i <= 10; i += 1) {
    print("fib(" + str(i) + ") =", fib(i));
}

// Iterative version, much faster for large values.
fn fib_iter(n) {
    var a = 0;
    var b = 1;
    for (var i = 0; i < n; i += 1) {
        var next = a + b;
        a = b;
        b = next;
    }
    return a;
}

print("fib_iter(50) =", fib_iter(50));
```

```text
fib(0) = 0
fib(1) = 1
fib(2) = 1
fib(3) = 2
fib(4) = 3
fib(5) = 5
fib(6) = 8
fib(7) = 13
fib(8) = 21
fib(9) = 34
fib(10) = 55
fib_iter(50) = 12586269025
```

The recursive version is exponential; the iterative one is linear. Both fit in
64-bit integers at these sizes.

## Collections

```spark
// Maps, for-in loops and text indexing.
var person = {"name": "Ada", "language": "C"};
print(person["name"], len(person));

person["age"] = 36;
print(person["age"], has(person, "age"), has(person, "height"));
print(person["missing"]); // nil

for (var key in person) {
    print(key, "->", person[key]);
}

var prices = {"apple": 10, "pear": 20, "banana": 30};
var total = 0;
for (var product in prices) {
    total += prices[product];
}
print("total:", total);

print("keys:", keys(prices));
print("values:", values(prices));

var letters = "";
for (var letter in "spark") {
    letters += letter;
}
print(letters);

print("spark"[0], substr("spark", 1, 3), len("ñandú"));
print(abs(-3), floor(2.9), max(4, 7), sqrt(81), round(2.5));
```

```text
Ada 2
36 true false
nil
language -> C
age -> 36
name -> Ada
total: 60
keys: ["banana", "pear", "apple"]
values: [30, 20, 10]
spark
s par 5
3 2 7 9 3
```

::: note
The map iteration order shown above is what this run produced; treat it as
unspecified. Sort `keys(map)` when order matters.
:::

## Closures

```spark
fn memoize(f) {
    var cache = [];
    return fn(n) {
        if (n < len(cache)) {
            var saved = cache[n];
            if (saved != nil) {
                return saved;
            }
        }
        var value = f(n);
        while (len(cache) <= n) {
            push(cache, nil);
        }
        cache[n] = value;
        return value;
    };
}

var fib = nil;
fib = memoize(fn(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
});

print("fib(1) =", fib(1));
print("fib(10) =", fib(10));
print("fib(50) =", fib(50));

fn make_counter() {
    var total = 0;
    return fn(increment) {
        total += increment;
        return total;
    };
}

var counter = make_counter();
print(counter(5), counter(3), counter(2));
```

```text
fib(1) = 1
fib(10) = 55
fib(50) = 12586269025
5 8 10
```

`memoize` closes over `cache`; `fib` is assigned after the closure is created,
which is why the closure sees the later binding. `make_counter` shows capture by
reference: two calls share `total`.

## Sorting

```spark
fn sort(values) {
    var copy = [];
    for (var i = 0; i < len(values); i += 1) {
        push(copy, values[i]);
    }

    var n = len(copy);
    for (var i = 0; i < n; i += 1) {
        for (var j = 0; j < n - i - 1; j += 1) {
            if (copy[j] > copy[j + 1]) {
                var temporary = copy[j];
                copy[j] = copy[j + 1];
                copy[j + 1] = temporary;
            }
        }
    }
    return copy;
}

fn median(values) {
    var sorted = sort(values);
    var n = len(sorted);
    if (n % 2 == 1) {
        return sorted[(n - 1) / 2];
    }
    return (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
}

var data = [5, 3, 9, 1, 7, 2, 8];
print("original:", data);
print("sorted:", sort(data));
print("median:", median(data));
assert(data[0] == 5, "sorting must not modify the original array");
```

```text
original: [5, 3, 9, 1, 7, 2, 8]
sorted: [1, 2, 3, 5, 7, 8, 9]
median: 5
```

This example defines its own `sort`, shadowing the native. It demonstrates a
copy, nested loops and `assert`. In production, use the native `sort` and
`sort_by`, which are stable O(n log n) merge sorts:

```spark
var data = [5, 3, 9, 1, 7, 2, 8];
sort(data);
print(data);   // [1, 2, 3, 5, 7, 8, 9]
```

## Echo server

```bash
spark examples/echo_server.spark
```

The server prints its port, accepts connections forever and spawns a coroutine
per client:

```spark
var port = 0;
if (len(argv) > 1) {
    port = int(argv[1]);
}

var server = tcp_listen("127.0.0.1", port);
print("listening " + str(server.port()));

while (true) {
    var client = server.accept();
    spawn(fn() {
        while (true) {
            var line = client.recv_line();
            if (line == nil) {
                break;
            }
            client.send(line + "\n");
        }
        client.close();
    });
}
```

```bash
printf 'hello\n' | nc 127.0.0.1 <port>
```

```text
hello
```

See [Sockets and Timeouts](@networking/sockets) for the full explanation.

## HTTP server

```bash
spark examples/http_server.spark
```

```bash
curl http://127.0.0.1:8080/
```

```text
Hello from Spark!
```

```bash
curl -X POST --data 'ping' http://127.0.0.1:8080/echo
```

```text
ping
```

It is built on `lib/http.spark`; see [HTTP Server](@networking/http-server).

## HTTP client

```bash
spark examples/http_client.spark https://example.com/
```

It prints the status, every response header and the body. HTTPS verifies the
certificate and host name; there is no flag to disable verification. See
[HTTP Client](@networking/http-client).

## WebSocket echo

The pair `examples/ws_echo_server.spark` and `examples/ws_echo_client.spark`
talk to each other over the loopback interface:

```bash
spark examples/ws_echo_server.spark 0     # terminal 1, prints the port
spark examples/ws_echo_client.spark ws://127.0.0.1:PORT/   # terminal 2
```

The server accepts a TCP connection, upgrades it with `ws_accept` and echoes
every text or binary message until the client closes:

```spark
var server = tcp_listen("127.0.0.1", port);
print("Serving ws://127.0.0.1:" + str(server.port()) + "/");

while (true) {
    var transport = server.accept();

    if (transport == nil) {
        continue;
    }
    try {
        var ws = ws_accept(transport, 5000);

        while (true) {
            var frame = ws.receive();
            if (frame == nil) {
                break;
            }
            if (frame.opcode == "text") {
                ws.send_text(frame.data);
            } else if (frame.opcode == "binary") {
                ws.send_binary(frame.data);
            }
        }
    } catch {
        // The client went away or broke the protocol; serve the next one.
    }
}
```

The client sends one message, prints the echoed frame and closes:

```text
echo: text hello from spark
closed: nil
```

The test suite runs the pair against each other, so the example stays honest.
See [WebSockets](@networking/websockets).

## Discord bot

```bash
python3 tests/run_tests.py --mock-gateway   # terminal 1
DISCORD_TOKEN=test-token \
DISCORD_GATEWAY_URL="ws://127.0.0.1:PORT/?v=10" \
spark examples/discord_bot.spark            # terminal 2
```

```text
ready
message: ping
reply sent
closed
```

It identifies, heartbeats and answers a `MESSAGE_CREATE` whose content is
`ping`. The token stays in the environment and is never printed. See
[WebSockets](@networking/websockets).

## Regex tokenizer

`examples/regex_tokenizer.spark` splits a line on whitespace, recovers each
field's character offset and classifies it with capture groups:

```bash
spark examples/regex_tokenizer.spark
```

```text
 0  name    let
 4  name    total
10  op      =
12  number  3
14  op      +
16  number  4
18  op      *
20  name    count
```

The full source is on the [Files, System and Data](@stdlib/files-and-system#tokenizing-a-line)
page, next to the regex reference it exercises.

## Running the whole set

```bash
for file in examples/*.spark; do
    echo "== $file"
    spark "$file"
done
```

The server examples run forever, so stop them with Ctrl-C, and the client
examples need an argument (a URL or a port). The test suite lints every example
and runs the network ones against local counterparts.