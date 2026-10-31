Spark has cooperative, single-threaded concurrency. A coroutine runs a function
concurrently with the rest of the program; channels move values between
coroutines. There are no OS threads, no locks and no data races: the running
coroutine keeps the CPU until it suspends itself.

## spawn and yield

```spark
fn worker(name) {
    print("start", name);
    yield;                     // suspend; the scheduler may run someone else
    print("end", name);
    return name + "!";
}

var a = spawn(worker, "a");
var b = spawn(worker, "b");

print("main");
print(a.join(), b.join());
```

```text
main
start a
start b
end a
end b
a! b!
```

`spawn(fn, args...)` queues a coroutine and returns its handle. It does not
switch immediately: the new coroutine starts as soon as the current one
suspends or blocks. The scheduler is FIFO, so runnable coroutines take turns in
the order they became ready.

The main script is itself a coroutine, so it can `yield` and use channels.
When the main coroutine finishes, the program ends and any pending coroutines
are abandoned.

## Coroutine handles

| Call | Result |
| --- | --- |
| `c.join()` | Blocks until `c` finishes and returns its result. |
| `c.done()` | `true` once `c` has finished. |

Joining the running coroutine is an error. `spawn` validates the function and
its arity before queueing, so a mismatch is reported at the `spawn` call.

```spark
var job = spawn(fn(x) => x * 2, 21);
print(job.join());     // 42
```

## Channels

A channel is a FIFO queue between coroutines.

- `channel()` is an unbuffered **rendezvous** channel: a sender blocks until a
  receiver takes the value.
- `channel(n)` is buffered: it holds up to `n` values before senders block.
  The capacity must be a non-negative integer.

| Call | Result |
| --- | --- |
| `ch.send(value)` | Sends, blocking while the channel is full. Errors when closed. |
| `ch.receive()` | Returns the next value, blocking while empty. `nil` once closed and drained. |
| `ch.close()` | Closes the channel: waiting receivers get `nil`, waiting senders get an error. |

```spark
var ch = channel();

fn producer() {
    for (var i in range(3)) {
        ch.send(i);
    }
    ch.close();
}

fn consumer() {
    var total = 0;
    while (true) {
        var value = ch.receive();
        if (value == nil) {
            break;
        }
        total += value;
    }
    return total;
}

spawn(producer);
print(spawn(consumer).join());   // 3
```

Values still buffered when a channel closes are delivered before `receive`
starts returning `nil`. Closing an already closed channel is allowed.

::: warning `nil` is both a value and the close signal
`receive` returns `nil` when the channel is closed and drained. If you need to
send `nil` as data, wrap values in a map (`{"value": nil}`) or use a sentinel
value such as `{"done": true}`.
:::

## Buffered channels

```spark
var queue = channel(2);

queue.send("a");
queue.send("b");        // buffer is now full; the next send would block

print(queue.receive()); // a
print(queue.receive()); // b
```

A buffered channel decouples producer and consumer speeds up to its capacity,
but it does not create parallelism: work happens one coroutine at a time.

## Deadlock detection

Blocking when no other coroutine can make progress aborts the program:

```text
RuntimeError: deadlock: every coroutine is blocked
```

That is preferable to hanging silently. Make sure at least one coroutine can
eventually run when using rendezvous channels.

## Suspension rules

`yield` and the blocking forms of `send`, `receive` and `join` are only allowed
in the outermost loop of a coroutine. Inside a callback passed to `map`,
`filter`, `each`, `sort_by` or another higher-order native, or inside an
imported module, they raise a `RuntimeError` instead of suspending.

```spark
// RuntimeError: cannot yield inside a native callback
map([1, 2, 3], fn(x) {
    yield;
    return x;
});
```

The same guard applies to a socket call that would block. Collect the work in
the coroutine body; use callbacks for pure transformations.

## Blocking I/O yields the coroutine

Socket operations participate in the same scheduler. A call that would block
registers a wait on its descriptor, and the scheduler sleeps in `poll(2)` until
the descriptor is ready or the nearest deadline fires. One process can serve
many connections:

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

var server = tcp_listen("127.0.0.1", 8080);

while (true) {
    var client = server.accept();
    if (client != nil) {
        spawn(echo, client);
    }
}
```

This is the pattern behind `examples/echo_server.spark`. See
[Networking](@networking/sockets) for timeouts, TLS, HTTP and WebSockets.

## GC and blocked coroutines

The collector traces blocked coroutines, their stacks and the locals they
captured, so calling `gc()` never breaks a pending `send`, `receive` or `join`.
Coroutines waiting on sockets are rooted through the scheduler's waiter list.

## Patterns

### Worker pool

```spark
fn make_worker(jobs, results) {
    return fn() {
        while (true) {
            var job = jobs.receive();
            if (job == nil) {
                break;
            }
            results.send(job * job);
        }
    };
}

var jobs = channel(4);
var results = channel(4);

var workers = [];
for (var i = 0; i < 3; i += 1) {
    push(workers, spawn(make_worker(jobs, results)));
}

for (var n in range(1, 6)) {
    jobs.send(n);
}
jobs.close();

var total = 0;
for (var i = 0; i < 5; i += 1) {
    total += results.receive();
}
print(total);   // 55
```

### Pipeline

```spark
var input = channel();
var output = channel();

spawn(fn() {
    while (true) {
        var value = input.receive();
        if (value == nil) {
            output.close();
            break;
        }
        output.send(value * 2 + 1);
    }
});

input.send(1);
input.send(2);
input.send(3);
input.close();

while (true) {
    var value = output.receive();
    if (value == nil) {
        break;
    }
    print(value);   // 3 5 7
}
```

### Timeouts with sockets

Channels themselves have no timeout. For network work, use the socket or
WebSocket timeout arguments, which raise `TimeoutError` and let the coroutine
continue; see [Sockets and Timeouts](@networking/sockets).

## Limits

- Coroutines are cooperative and single-threaded; there are no OS threads and
  no parallelism.
- Each coroutine keeps its own operand stack (up to 4,194,304 values) and up
  to 4096 call frames.
- A channel holds up to 16,777,216 values.
- An uncaught error in any coroutine aborts the whole program.

See [Limits and Performance](@internals/limits-and-performance) and
[Architecture](@internals/architecture#asynchronous-io) for the scheduler
internals.

## Next

- [Sockets and Timeouts](@networking/sockets) — I/O that uses the scheduler.
- [Errors and Exceptions](@guide/errors-and-exceptions) — failures across tasks.
- [Example Gallery](@appendix/examples) — the echo server and Discord client.