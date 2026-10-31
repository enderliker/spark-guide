Spark is a bytecode interpreter written in C11. The only external dependency is
OpenSSL, linked solely for the TLS transport. This page follows one program from
source text to result.

## The pipeline

```
 .spark source
      │  lexer.c         tokens with line numbers
      ▼
 parser.c ──► AST in an arena (ast.c)
      │  compiler.c      scope resolution and bytecode emission
      ▼
 Chunk (bytecode + constants + lines)
      │  vm.c            value stack, frames, closures, GC
      ▼
 result / error
```

The stages are deliberately separate:

1. **Lexer** turns text into tokens with line numbers, handling keywords,
   numbers, string escapes, interpolation and comments.
2. **Parser** builds an AST with recursive descent and precedence climbing. AST
   nodes live in an arena (`ast.c`) that is freed all at once when compilation
   finishes. The first error aborts through `setjmp`/`longjmp`.
3. **Compiler** walks the AST, resolves locals and upvalues, and emits bytecode
   into a `Chunk`.
4. **VM** executes the bytecode on a value stack with call frames, closures and
   a mark-and-sweep collector.

## Source tree

| File | Responsibility |
| --- | --- |
| `main.c` | CLI, file reading, REPL. |
| `lexer.c` | Tokens, keywords, numbers, strings, comments. |
| `parser.c` | Recursive descent, precedences, AST construction. |
| `ast.c` | Arena allocator; the whole AST is freed at once. |
| `compiler.c` | Scopes, locals, upvalues, constant folding, code emission. |
| `chunk.c` | Code, lines and constants arrays; disassembler. |
| `vm.c` | Stack, frames, closures, natives, errors, GC, scheduler. |
| `object.c` | Dynamic objects, string interning, arrays, maps, formatting. |
| `bytes.c` | The `bytes` constructors and `bytes_builder` natives. |
| `net.c` | Sockets, TLS, URLs, HTTP, and WebSocket clients and servers. |
| `json.c` / `regex.c` | JSON and regular-expression engines. |
| `codec.c` | base64/hex codecs and the bounded DEFLATE/gzip decoder. |
| `crypto.c` | SHA-256, HMAC-SHA256 and the CSPRNG through OpenSSL. |
| `datetime.c` | Date/time formatting and parsing. |
| `bytecode.c` | `.sparkc` serialization. |
| `debugger.c` | Interactive debugger. |
| `formatter.c` / `linter.c` | Developer tools. |
| `table.c` | Global name-to-slot hash table (open addressing, tombstones). |
| `memory.c` | Byte accounting and GC threshold. |
| `error.c` | Diagnostics and source carets. |
| `buf.c` | Auxiliary dynamic buffer. |
| `value.h` | `Value` and the `Obj` header. |

## Values and objects

A `Value` is a tagged union:

```c
typedef struct {
    ValueType type;              /* VAL_NIL, VAL_BOOL, VAL_NUMBER, VAL_INT, VAL_OBJ */
    union { bool boolean; double number; int64_t integer; Obj *obj; } as;
} Value;
```

Two numeric tags exist: `VAL_NUMBER` (`double`) and `VAL_INT` (`int64_t`).
Arithmetic and comparison promote an integer to a double when they must, but two
integers stay exact. Overflow-checked helpers (`int_add_overflow`,
`int_sub_overflow`, `int_mul_overflow`) fall back to a double when the result
does not fit, so C signed overflow never happens.

Equality (`values_equal`) treats an integer and a whole double as equal, and
`hash_value` canonicalizes a whole double to its integer, so `map[1]` and
`map[1.0]` are the same key.

Every dynamic value shares an `Obj` header:

```c
struct Obj {
    ObjType type;
    bool marked;      /* GC mark */
    Obj *next;        /* all objects, linked */
};
```

Concrete object types include:

- `ObjString` — FNV-1a hash, length and inline bytes. All strings are
  **interned**, so equal strings share one object and equality can start with a
  pointer comparison.
- `ObjBytes` — immutable, non-NUL-terminated byte buffer with an inline payload
  (`unsigned char data[]`). Bytes are **not** interned, so two equal byte
  sequences are distinct objects that compare equal by content; map hashing and
  key comparison look inside them. A `bytes` value never reaches the constant
  pool because the language has no literal for it.
- `ObjBytesBuilder` — growable `malloc`ed buffer, the mutable companion of
  `bytes`.
- `ObjArray` — dynamic array of `Value`.
- `ObjMap` — open-addressing table with cached hashes, tombstones and
  specialized probing for object and string keys.
- `ObjFunction` — code, arity, minimum arity (defaults), varargs flag, upvalue
  count, name.
- `ObjClosure` — function plus captured upvalues.
- `ObjUpvalue` — points to a stack slot or to its closed copy.
- `ObjNative` — C function pointer, arity (`-1` for variadic), name.
- `ObjFile`, `ObjSocket`, `ObjServer`, `ObjWebSocket` — GC-managed resources
  with finalizers.
- `ObjCoroutine` — private stack, frames, try handlers, scheduler links, wait
  state and result.
- `ObjChannel` — FIFO buffer plus blocked sender and receiver queues.
- `ObjStringBuilder` — growable buffer for O(1) amortized appends.

### String concatenation

Strings are immutable and interned. `s += x` allocates a new string and copies
the accumulator, so building an N-character string one piece at a time is
O(N²). This is the same trade-off Python and Lua make. `string_builder` owns a
`malloc`ed buffer that doubles when full, so appends are amortized O(1);
`sb_to_string` copies once through the interning path.

The project considered in-place mutation under uniqueness, rope strings and
promoting accumulators at compile time, and rejected them for escape-tracking
risk, flattening cost and hot-path complexity respectively. The explicit
builder buys the guarantee without changing string semantics.

### Bytes are a sibling of strings, not a reinterpretation

`bytes` is its own `Obj` type with its own constructors in `bytes.c`, rather
than a flag on `ObjString`. Strings stay interned and UTF-8-validated, which
their equality, hashing and every text native rely on; bytes are neither
interned nor validated, and consumers index them 0..255. The two types never
convert implicitly, so no text native had to grow a binary mode.

The binary path stays inside C: `read_bytes`, `recv_bytes` and the WebSocket
frame parser hand back `ObjBytes` directly, `codec.c` decodes base64/hex and
DEFLATE into one, and `crypto.c` returns digests as one. The decoder in
`codec.c` follows the structure of Mark Adler's puff.c and checks its output
against a 16 MiB cap while it writes, so a decompression bomb fails before it
allocates the expanded size.

## The compiler

- Each function has its own `Compiler` linked to the enclosing one, so lexical
  captures resolve in a single pass.
- Scopes track `scope_depth` and a stack of locals. Closing a scope emits `POP`
  or `CLOSE_UPVALUE`.
- Non-local variables become globals resolved at compile time.
  `vm_global_slot` returns a stable 16-bit slot; `global_names` only maps names
  to slots and persists across REPL lines. At runtime, global instructions index
  `vm.global_slots` directly, with no hashing.
- Loops keep lists of pending `break` and `continue` jumps to patch, and labels
  are part of the loop context chain.
- `switch` evaluates its subject once into a hidden local; cases have their own
  scopes and do not fall through.
- String interpolation compiles each `${...}`, converts it with `TO_STRING` and
  concatenates with `ADD`.
- `const` is tracked per local, upvalue and global slot. A global constant is
  defined with `DEFINE_GLOBAL_CONST`, which marks the slot when the declaration
  executes.
- Compound assignments reuse `DUP2` + `INDEX` so the array and index are not
  evaluated twice.
- **Tail calls**: `return f(...)` emits `TAIL_CALL`, which closes open upvalues,
  copies arguments into the current frame's slots, resets the instruction
  pointer and constants, and runs the target without a new frame.
- **Default parameters** use `min_arity` plus `DEFAULT_ARG slot offset` in the
  function preamble.
- **Varargs and spread** collect extras into an array and use
  `CALL_SPREAD`/`TAIL_CALL_SPREAD` to flatten arguments.
- **Constant folding and dead-code elimination** evaluate constant arithmetic,
  bitwise operations, comparisons, concatenation, ternaries and `??` at compile
  time. Potential runtime errors (division by zero, negative shifts) are left
  for runtime so the error is precise. Unreachable statements after `return`,
  `throw`, `break` or `continue` are dropped.

See [Bytecode and Dispatch](@internals/bytecode-and-dispatch) for the
instruction set and fusion rules.

## Stack and frames

The value stack grows dynamically from 2048 to 4,194,304 values (64 MB). On
reallocation, interior pointers are rebased: `vm.stack_top`, every
`frame.slots` and every open upvalue's `location`.

```c
typedef struct {
    ObjClosure *closure;
    uint8_t *ip;
    Value *slots;
    Value *constants;   /* cached constant pool */
} CallFrame;
```

For `fn f(a, b)` the stack looks like:

```
... callee  arg1  arg2 | slot0=closure  slot1=a  slot2=b  ...
                        └─ frame->slots
```

`OP_RETURN` closes open upvalues, discards the frame down to `slots`, pushes the
result and resumes the caller. There are at most 4096 frames.

## Upvalues

An open upvalue points at the stack. The VM keeps the open list sorted by
descending address and reuses an existing upvalue when a variable is captured
twice. When the scope closes, the value is copied into `closed` and `location`
is repointed, so the closure keeps working after the frame disappears.

## Modules

`import` emits `OP_IMPORT`. The VM canonicalizes paths with `realpath()` and
appends `.spark` when needed. A `MODULE_LOADING` marker detects cycles and
succeeds without re-execution; `MODULE_LOADED` guarantees each file executes at
most once. Modules share the global namespace.

## Exceptions

A runtime stack of try handlers records the handler kind, target IP, frame
index, stack depth and try nesting depth. `throw` scans the handler stack,
unwinds intervening frames, closes their open upvalues and jumps to the handler
with the value pushed. `finally` handlers run during unwinding and
`OP_END_FINALLY` resumes propagation if the exception was not caught. With no
handler, the VM halts with `uncaught exception`.

## The object model

- Maps act as objects: `receiver.method(args)` emits `OP_INVOKE`, which looks up
  a closure in the map and binds `self`.
- Classes are objects with methods and static members. An instance carries its
  class and an own field map; method lookup walks the superclass chain.
- `self` resolves to `OP_SELF`, which reads `frame->self`; a standalone call
  raises `NameError`.

## Asynchronous I/O

The scheduler integrates with `poll(2)`:

- Sockets are non-blocking. Each operation first tries a non-blocking syscall;
  `EWOULDBLOCK` registers a waiter and returns `INTERPRET_BLOCKED`.
- A waiter records the coroutine, the pending operation, the awaited resource,
  the readiness bits and an absolute monotonic deadline.
- The scheduler polls after each coroutine switch and sleeps until the nearest
  deadline when the run queue empties. There is no fixed granularity.
- Woken coroutines are enqueued through `vm_wake_coroutine`.
- The waiter list is a GC root, and coroutines trace their awaited resources.
- A would-block call inside a callback or module (`run_depth > 1`) raises
  instead of suspending.

TLS uses the same wait list; OpenSSL's `WANT_READ`/`WANT_WRITE` flips the poll
direction. The HTTP client is synchronous and uses a blocking handshake and
reader bounded by the request deadline.

## Tooling internals

- **Debugger**: normal execution never checks breakpoints. `--debug` routes
  execution through the cold dispatch path, where instruction and line
  boundaries check breakpoints and stepping. Local names are recorded during
  compilation.
- **Formatter**: validates syntax with the parser, then scans tokens,
  preserving comments and interpolations while normalizing whitespace and
  indentation. Idempotence is tested.
- **Linter**: a single-pass AST traversal for unused variables, unreachable
  code and shadowing.
- **Bytecode serialization**: magic `SPRK`, format version `5`, active global
  names, then chunks, line/column tables and constants recursively. Constants
  carry `nil`, `bool`, `int`, `number`, `string` or `function`; there is no
  `bytes` tag because no `bytes` value can appear in a constant pool.

## Extending the interpreter

### Add a native

1. Write `static Value my_native(int argc, Value *args)` in the relevant module
   (`vm.c` for core, `net.c` for network).
2. Keep arguments on the stack and push the result before releasing anything,
   because allocation can trigger the collector.
3. Register it with `define_native("my_native", my_native, arity)`; use `-1`
   for variadic and validate by hand.
4. To fail, call `vm_runtime_error(...)` and return `NIL_VAL`.
5. Add it to the reference documentation and a test fixture.

### Add an instruction

1. Add the opcode to `chunk.h` and to `opcode_name`/the disassembler.
2. Emit it from `compiler.c` with `emit_byte` / `emit_u16`.
3. Implement it in the `switch` in `run()` in `vm.c`, keeping the stack
   balanced on every path.
4. Update the documentation and add a test.

## Testing

`tests/run_tests.py` runs:

- `tests/cases/*.spark` against exact `.out` output;
- `tests/errors/*.spark` against an exit code and a `stderr` fragment;
- REPL sessions and the CLI flags (`--version`, `--help`, `--dump`,
  `--compile`, `--debug`, `--format`, `--lint`, bytecode execution);
- local network fixtures: an HTTP server, an RFC 6455 server and client, the
  `ws_accept` server handshake probes, a mock Discord gateway and a
  low-`RLIMIT_NOFILE` run.

The suite never contacts the public internet. It also runs under
AddressSanitizer and UndefinedBehaviorSanitizer, and CI builds with `-Werror`.

## Next

- [Bytecode and Dispatch](@internals/bytecode-and-dispatch) — the instruction set.
- [Garbage Collector](@internals/garbage-collector) — memory management.
- [Limits and Performance](@internals/limits-and-performance) — the numbers.