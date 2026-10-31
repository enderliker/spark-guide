This page records where Spark stands and what the project intends to do next.
It summarizes `CHANGELOG.md` and `tasks/plan.md`; the plan is the source of
truth when the two disagree.

## Current status

**Spark 0.1.0** was released on 2026-10-27 with the language core, the standard
library, the tooling and the collector. A second stream that was still
unreleased at the time of writing adds coroutines, channels, sockets, TLS, the
HTTP client, the Spark HTTP server library and the WebSocket client. That work
is in the tree and in the test suite, and it is what this wiki documents.

| Area | State |
| --- | --- |
| Language core | Complete for 0.1.0. |
| Classes, closures, exceptions, modules | Complete. |
| Standard library | Text, collections, math, files, system, JSON, regex, builders. |
| Coroutines and channels | Implemented in the unreleased stream. |
| TCP/UDP, TLS, HTTP client | Implemented; TLS verifies by default. |
| HTTP server | `lib/http.spark`, written in Spark; one connection at a time. |
| WebSocket | Client only. No server yet. |
| Debugger, formatter, linter, bytecode files | Complete. |
| Test suite | 243 tests, including offline network fixtures. |

The measured reference on the development machine (WSL2, shared) is a `fib(27)`
minimum around **4.95 ms** against a gate of **5 ms**, with all 243 tests
passing and clean AddressSanitizer/UndefinedBehaviorSanitizer runs.

## Known gaps

These are the limits you will meet while using 0.1.0.

### Language

- No binary type. `string` is UTF-8 text; holding arbitrary bytes in it is not
  supported. This is why the WebSocket server is missing: frame handling needs a
  byte buffer.
- No insertion-order guarantee for maps. Iteration order is unspecified;
  `keys(map)` must be sorted when order matters.
- No loop `else`, no `break value`, no multiple assignment.
- Missing object protocols: `__iter__`, `__call__`, `__contains__`, `__bool__`,
  `__hash__`.
- Instances cannot be map keys.
- No getters, no `enum`, no `private`/`readonly`, no `defer`.
- `try`/`catch` exposes `type`, `message`, `line` and `column`, but there is no
  stack trace.
- Top-level variables in a file are globals, so top-level loops miss the fused
  superinstructions. The REPL keeps globals on purpose.
- No module namespaces; modules share the global namespace.

### Libraries

- The regex engine is a Pike VM with leftmost-longest semantics. It has no
  `{n,m}` quantifiers, no lazy quantifiers, no capture groups and no `\b`.
- No base64/hex codecs, no date formatting, no hashing or randomness beyond
  `rand`/`srand`.
- The HTTP client is synchronous and blocks the process; it does not yield its
  coroutine. There is no gzip, no keep-alive and no connection reuse.
- The Spark HTTP server handles one connection at a time and has no keep-alive.
- No WebSocket server, no `permessage-deflate`, no reconnect helper.

### Runtime

- Cooperative, single-threaded coroutines. There is no preemption and no OS
  threading.
- Non-compacting mark-and-sweep GC; no generations and no arena yet.
- No JIT or ahead-of-time native compilation; the bytecode VM is the only
  execution mode.
- No package manager, no lockfile, no language server.
- Not a security sandbox: `exec`, the filesystem and the network are available
  to every program.

## Roadmap: 0.2

The 0.2 stream is organized in phases. Each phase ends at a green checkpoint
(build, tests, sanitizers, benchmark gate) and phases are independently
shippable, so lower-priority work can be cut without leaving half a feature.

| Phase | Priority | Scope |
| --- | --- | --- |
| 21. Coherence | P0 | Reference fixes, English-only artifacts, error-message corrections. |
| 22. `bytes` | P1 | Immutable byte strings, binary file and socket I/O, WebSocket server. |
| 23. Libraries | P1 | Base64/hex, inflate, `format`, dates, SHA-256/HMAC, full regex, math and text conveniences. |
| 24. Network hardening | P1 | gzip, keep-alive, coroutine-aware HTTP client, concurrent HTTP server. |
| 25. Ergonomics | P2 | Loop `else`, `break value`, multiple assignment, object protocols, error traces, ordered maps, getters and `enum`. |
| 26. Performance | P2/P3 | Arena allocator, GC observability and generations, global-path superinstructions, cheaper coroutines, LTO/PGO. |
| 27. Tooling | P3 | `--check`/`-e`/`--time`, REPL editing, tree-sitter grammar, embedding header, module namespaces, fuzzing. |

Phase 21 is complete. The others are planned; the checkboxes in `tasks/plan.md`
are the live status.

### The `bytes` type

A first-class immutable byte-string object, sibling of `string` rather than a
reinterpretation of it. Indexing yields integers `0..255`, `len` counts bytes,
equality is by content, and `bytes_builder()` provides mutation. `string` keeps
its UTF-8 character semantics, so no existing program changes meaning, and the
two types are never converted implicitly; mixed operations raise `TypeError`
naming `to_bytes`/`to_string`.

This unblocks binary file and socket I/O and the WebSocket server.

### Libraries

- `base64_encode`/`base64_decode`, `hex_encode`/`hex_decode`.
- Deflate/gzip decode with a vendored `inflate` in `src/codec.c`; no zlib
  dependency and a decompression size cap.
- `format` with printf-style placeholders.
- Date/time formatting and parsing.
- `sha256`, `hmac_sha256` and `rand_bytes` through OpenSSL.
- Regex: `{n,m}`, lazy quantifiers, flags, match offsets, capture groups,
  `regex_split`, and group references in `regex_replace`. The engine moves to
  Perl/JavaScript leftmost-first semantics, which is a documented breaking
  change for alternation patterns such as `a|ab`.
- Math natives, plus string and collection conveniences.

### Networking

- The existing `http_*` helpers become coroutine-aware in place, instead of
  shipping a parallel `*_async` API. This removes the "HTTP client is
  synchronous" limit and is a breaking change.
- gzip decoding and keep-alive/connection reuse.
- A Spark HTTP server that serves several clients concurrently with bounded
  request bodies.
- A WebSocket keepalive/reconnect helper, once `bytes` lands.

### Ergonomics and protocols

- `else` on loops, `break value`, multiple assignment and swaps.
- `__iter__`, `__call__`, `__contains__`, `__bool__`, `__hash__` and reflected
  operators.
- `trace` on errors and a built-in `Error` hierarchy.
- `to_json` for instances and pretty printing.
- Insertion-ordered maps: the hash table remains for lookup, but iteration order
  becomes specified behavior.
- Getters and `enum`.
- `private`/`readonly` stay out: enforcing them in a dynamic language costs a
  runtime check on every field access, and the linter can flag the obvious
  cases for free. `defer` stays out because `try`/`finally` covers it.
- Module namespaces and `import ... as`; the package manager is deferred to a
  later stream.

### Performance

The project measures every VM change instead of guessing:

- Object arena with free lists, then GC statistics and environment tuning,
  then a generational nursery.
- Superinstructions for the global path and the loop idiom.
- Script scoping for top-level variables in files only; the REPL keeps globals
  and module-visible names stay global.
- Scheduler changes that remove an extra `poll(2)` per turn, and smaller initial
  coroutine stacks.
- LTO and PGO build targets.
- NaN-boxing is an explicit go/no-go point after the benchmark suite gains
  function-body variants; dropping it is a valid outcome.

The `fib(27)` gate of **under 5 ms** does not move for the GC work. An
optimization that cannot hold it does not land.

### Tooling and ecosystem

- CLI: `--check`, `-e`, `--time`, `--gc-stats` and `--` argument separation.
- REPL line editing and history.
- Linter checks for undefined globals and unused imports.
- A tree-sitter grammar with queries and editor files. There is no language
  server in 0.2, and that is deliberate: the grammar also gives the formatter
  and the linter a second parser to check against.
- An experimental public embedding header (`src/spark.h`) and a static library
  target, explicitly not ABI-stable before 1.0.
- Standard library modules written in Spark under `lib/`.
- Parser/lexer fuzz targets, a coverage threshold and multi-platform release
  artifacts.

## Decisions in force

| Decision | Choice |
| --- | --- |
| Dependencies | OpenSSL only, for TLS. Deflate vendors its own inflate. |
| Breaking changes | Allowed before 1.0, never silent; recorded in `CHANGELOG.md`, the reference and the fixtures in the same commit. |
| Benchmark gate | `fib(27)` min < 5 ms, plus a per-task target measured with `run_all.py`. |
| HTTP concurrency | Make the existing client coroutine-aware in place; no parallel async API. |
| Regex semantics | Move to leftmost-first with lazy quantifiers. |
| Maps | Insertion order becomes specified. |
| Editor support | tree-sitter, no LSP in 0.2. |
| Packaging | Module namespaces in 0.2; manifest, resolver and lockfile later. |
| Tests | Never touch the public internet; every blocking native has a bounded default timeout. |

## Out of scope

- JIT/AOT native code generation and a register-based VM.
- OS threads on top of the coroutines.
- HTTP/2, HTTP/3/QUIC, proxies, cookies and streaming request bodies.
- `permessage-deflate` and server-side sharding/rate limiting.
- Windows-native sockets and TLS; WSL is the supported Windows path.
- A non-blocking DNS resolver; resolution keeps using `getaddrinfo`.
- Deleting `exec` or sandboxing the runtime.

## Contributing

Every change must satisfy the project's definition of done:

- the build is warning-free under `-O3 -Wall -Wextra -Wpedantic`;
- `python3 tests/run_tests.py` passes and new behavior has fixtures;
- sanitizer runs are clean for VM, GC or compiler work;
- `fib(27)` stays under 5 ms unless the task targets performance;
- documentation is updated where behavior changes, and all artifacts are in
  English;
- tests use local servers and ephemeral ports, never the public internet.

See `README.md`, `docs/language.md`, `docs/architecture.md` and `AGENTS.md` in
the repository for the full rules.

## Next

- [Example Gallery](@appendix/examples) — the runnable programs.
- [Limits and Performance](@internals/limits-and-performance) — the measured numbers.
- [Introduction](@getting-started/introduction) — start from the beginning.