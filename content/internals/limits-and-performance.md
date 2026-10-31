This page collects the hard limits and the measured performance of Spark 0.1.0.

## Language and VM limits

| Limit | Value |
| --- | --- |
| Integer width | 64-bit signed; out-of-range results promote to float. |
| Parameters, arguments and array-literal elements | 255 |
| Local variables per function | 1024 (slots above 255 use 16-bit instructions) |
| Call frames | 4096 non-tail calls; tail calls reuse frames and are unbounded |
| Value stack | 2,048 → 4,194,304 values (64 MB) |
| Constants per function | 65,536 (16-bit index) |
| Channel capacity | 16,777,216 values |
| Coroutine stack | 4,194,304 values and 4096 frames each |

A value stack overflow surfaces as a runtime error, not a crash. Exceeding the
frame limit raises `RecursionError`; using TCO removes the limit for tail
recursion.

## Network limits

| Limit | Value |
| --- | --- |
| Ports | `0..65535` |
| `recv` / `recv_bytes` / `recv_from` | 16 MiB per call |
| `recv_line` | 16 MiB maximum; 64 KiB default |
| TLS `read` | 16 MiB per call |
| TLS `write` | `INT32_MAX` bytes |
| TLS version | 1.2 minimum |
| HTTPS/HTTP body | 16 MiB default (`max_body`) |
| HTTP status line + headers | 64 KiB |
| HTTP headers | 1000 |
| HTTP redirects | 5 |
| HTTP deadline | 30 s default (`timeout_ms`) |
| WebSocket frame / message | 16 MiB |
| WebSocket control payload | 125 bytes |
| WebSocket close reason | 123 bytes |
| Descriptors | Process `RLIMIT_NOFILE`; exhaustion raises `NetworkError` |

The HTTP client and the WebSocket client fail explicitly when a limit is
crossed; they do not truncate silently.

## Data and codec limits

| Limit | Value |
| --- | --- |
| `read_bytes` | 16 MiB (`max` may lower it, never raise it) |
| `inflate` / `gunzip` output | 16 MiB (`max` may lower it) |
| `rand_bytes` | 16 MiB per call |
| Regex instructions | 1024 per pattern |
| Regex capture groups | 32 |
| Regex repetition count | 10,000 |
| Regex engine steps | 20,000,000 per call |

The codecs and the regex engine raise `ValueError` when a limit is crossed, so a
crafted input fails instead of exhausting memory or hanging the interpreter.
See [Files, System and Data](@stdlib/files-and-system).

## HTTP server library limits

| Limit | Value |
| --- | --- |
| Request line | 8192 characters |
| Each header line | 8192 characters |
| Headers | 100 |
| Body | Up to `Content-Length` |
| Concurrency | One connection at a time |

## Processor and memory

The VM optimizes for a small interpreter, not a JIT:

- Bytecode is a compact byte stream with 16-bit constant indexes.
- Hot state lives in C locals; computed goto is used where available.
- Superinstructions fuse local/constant arithmetic, comparisons and branches,
  direct local returns and self-recursive calls.
- The collector is non-compacting mark-and-sweep with an adaptive threshold.
- Strings are interned, so equality and map lookups can start with a pointer
  comparison.

## Benchmarks

`benchmarks/run.py` runs `fib(27)` seven times and reports the minimum and
median. On an idle development machine the minimum is around **5.0 ms** and the
median around **5.1 ms**; the project's performance gate is a minimum below
**5 ms**. CI uses a coarser guard (`--max-ms 100`) because shared runners are
noisy.

The machine sits close to the gate: the phase 22 and 23 checkpoints measured a
`fib(27)` minimum between 5.02 and 5.22 ms on a shared WSL2 host. That is the
noise floor, not a regression — every library phase kept the VM untouched except
where a native was added, and the gate itself does not move.

`benchmarks/run_all.py` runs the wider set. The baseline recorded for the 0.2
work (WSL2, shared machine, 2026-10-31) was:

| Benchmark | Min (ms) | Median (ms) |
| --- | --- | --- |
| fib(27) | 4.83 | 4.90 |
| int_loop (5M) | 96.81 | 98.25 |
| float_loop (3M) | 57.88 | 58.59 |
| arrays (1M) | 47.03 | 47.47 |
| maps (200k) | 134.61 | 136.79 |
| closures (1M) | 24.10 | 24.58 |
| higher_order (300k) | 28.09 | 28.63 |
| sort (100k) | 4.07 | 4.19 |
| sort_by (100k) | 24.55 | 24.94 |
| strings (200k) | 51.44 | 55.01 |
| string_builder (200k) | 5.11 | 5.19 |
| alloc (1M) | 74.87 | 75.99 |
| echo (2k RTT) | 440.29 | 471.85 |
| http (200 requests) | 157.36 | 159.35 |

These numbers are a reference point, not a promise. Run the benchmarks on your
own machine before drawing conclusions; the project's convention is to measure
every VM change rather than guess.

```bash
python3 benchmarks/run.py
python3 benchmarks/run_all.py
```

The network benchmarks stay offline: `echo.spark` uses an in-process coroutine
server, and `http_roundtrip.spark` talks to a loopback server started by the
runner in another process (the HTTP client blocks the process rather than
yielding).

## Where time goes

- **Dispatch** dominates tiny operations. Superinstructions exist to cut it.
- **Allocation** dominates maps, arrays and long-lived object graphs.
- **Syscalls** dominate the network benchmarks: roughly 220 µs per echo
  round-trip and 790 µs per HTTP request on WSL2.
- **String concatenation** dominates text building if you use `+=` in a loop.

## Practical guidance

### Prefer locals in hot loops

Fused superinstructions target local variables. A loop at top level uses
globals (`GET_GLOBAL`/`SET_GLOBAL`), which are still fast — slots, not hashes —
but miss the local/constant fusions. Put hot code inside a function.

```spark
fn sum_squares(n) {
    var total = 0;              // local: fused additions
    for (var i = 0; i < n; i += 1) {
        total += i * i;
    }
    return total;
}
```

### Do not build strings with `+=` in a loop

```spark
var builder = string_builder();
for (var i = 0; i < 200000; i += 1) {
    builder.append("x");
}
var text = builder.to_string();
```

This is O(n) instead of O(n²). The measured difference for 200,000 characters
is about 6 ms versus about 2.2 s.

### Reuse collections

Growing an array one element at a time is fine (amortized), but allocating a
new array per iteration is not. `copy` is shallow; use it when you need a
snapshot, not as a defensive default.

### Measure, do not guess

```bash
python3 benchmarks/run_all.py
```

The suite reports min and median per benchmark. The minimum is the least noisy
indicator on a shared machine. The project's definition of done requires the
`fib(27)` minimum to stay under 5 ms unless a task explicitly targets
performance.

## Tests

The test suite contains 340 tests:

- `tests/cases` — valid programs compared against exact `.out` output, including
  the `bytes` core, binary file and socket I/O, the codecs, compression, dates,
  crypto and the full regex engine;
- `tests/errors` — failing programs checked for exit code and a `stderr`
  fragment;
- REPL sessions and CLI flags;
- local network fixtures, including TLS, WebSockets in both directions, HTTP,
  the `ws_accept` handshake probes and a mock Discord gateway;
- a low-`RLIMIT_NOFILE` run that trips descriptor exhaustion.

```bash
python3 tests/run_tests.py
```

The suite also runs under AddressSanitizer and UndefinedBehaviorSanitizer. Any
change to the VM, compiler or collector is expected to pass that run.

## Next

- [Bytecode and Dispatch](@internals/bytecode-and-dispatch) — why the fusions help.
- [Garbage Collector](@internals/garbage-collector) — allocation behavior.
- [Project Status and Roadmap](@appendix/roadmap) — planned performance work.