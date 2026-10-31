A Spark function compiles to a `Chunk`:

- `code[]` — instruction and operand bytes.
- `lines[]` — the source line of each byte, for errors and traces.
- `constants[]` — values addressed by a 16-bit index.

The VM is a stack machine. This page describes the instruction set, the fused
superinstructions, and the dispatch loop that makes it fast.

## Instruction groups

| Group | Instructions |
| --- | --- |
| Constants and stack | `CONSTANT`, `NIL`, `TRUE`, `FALSE`, `POP`, `DUP`, `DUP2` |
| Variables | `GET_LOCAL`, `SET_LOCAL`, `GET_LOCAL_16`, `SET_LOCAL_16`, `GET_GLOBAL`, `DEFINE_GLOBAL`, `DEFINE_GLOBAL_CONST`, `SET_GLOBAL`, `GET_UPVALUE`, `SET_UPVALUE` |
| Collections | `ARRAY n`, `ARRAY_PUSH`, `ARRAY_EXTEND`, `MAP n`, `INDEX`, `INDEX_SET`, `LEN`, `TO_STRING`, `ITER_KEYS` |
| Arithmetic and logic | `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`, `MODULO`, `INT_DIVIDE`, `BIT_AND`, `BIT_OR`, `BIT_XOR`, `SHL`, `SHR`, `EQUAL`, `GREATER`, `LESS`, `NOT`, `NEGATE`, `BIT_NOT` |
| Superinstructions | `ADD_LOCAL_CONST`, `SUBTRACT_LOCAL_CONST`, `MULTIPLY_LOCAL_CONST`, `DIVIDE_LOCAL_CONST`, `LESS_LOCAL_CONST`, `GREATER_LOCAL_CONST`, `JUMP_IF_NOT_LESS_LOCAL_CONST`, `JUMP_IF_NOT_GREATER_LOCAL_CONST`, `RETURN_LOCAL`, `RETURN_ADD`, `CALL_SELF_SUB_LOCAL_CONST` |
| Control | `JUMP`, `JUMP_IF_FALSE` (peek), `JUMP_IF_FALSE_POP` (consume), `LOOP` (16-bit offsets) |
| Functions | `CALL argc`, `CALL_SPREAD`, `TAIL_CALL argc`, `TAIL_CALL_SPREAD`, `DEFAULT_ARG slot offset`, `CLOSURE const [upvalues]`, `CLOSE_UPVALUE`, `RETURN` |
| REPL | `PRINT_REPL` |

Control-flow details:

- `JUMP_IF_FALSE` peeks at the top without popping; `and` and `or` use it so
  they can return the operand.
- `JUMP_IF_FALSE_POP` consumes the condition and is used by `if`, `while` and
  `for`, avoiding an extra `POP`.
- Jumps are emitted with a `0xffff` marker and patched once the target is known.
- `CLOSURE` is followed by an `(is_local, index)` pair per upvalue.
- `ITER_KEYS` normalizes a `for-in` iterable: arrays stay as they are, maps
  become an array of keys, strings become an array of one-character strings.
  `LEN` leaves the value and pushes its length, which `for-in` uses for its
  counter.

## A compiled function

```spark
fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}
```

```text
== fib ==
0000    2 JUMP_IF_NOT_LESS_LC    1 '2' -> 11
0006    3 RETURN_LOCAL          1
0008    2 JUMP                  8 -> 11
0011    5 CALL_SELF_SUB_LC      1 '1'
0015    | CALL_SELF_SUB_LC      1 '2'
0019    | RETURN_ADD
0020    1 NIL
0021    | RETURN
```

Every instruction here is a fusion:

- `JUMP_IF_NOT_LESS_LC` compares local slot 1 with the constant `2` and
  branches without pushing a boolean.
- `RETURN_LOCAL` returns a local directly.
- `CALL_SELF_SUB_LC` calls the currently executing function with `local -
  constant`, avoiding a global lookup and stack moves.
- `RETURN_ADD` computes the addition and returns it in one instruction.

The semantics are identical to the unfused sequence; only dispatch overhead
disappears. `--dump` abbreviates names: `_LC` means "local and constant" and
`_LL` means "two locals".

## Superinstructions

The compiler folds common patterns when the left operand is a local and the
right one is a numeric constant:

| Pattern | Instruction |
| --- | --- |
| `local + const` | `ADD_LOCAL_CONST` |
| `local - const` | `SUBTRACT_LOCAL_CONST` |
| `local * const` | `MULTIPLY_LOCAL_CONST` |
| `local / const` | `DIVIDE_LOCAL_CONST` |
| `local < const` | `LESS_LOCAL_CONST` |
| `local > const` | `GREATER_LOCAL_CONST` |
| `if (local < const)` | `JUMP_IF_NOT_LESS_LOCAL_CONST` |
| `if (local > const)` | `JUMP_IF_NOT_GREATER_LOCAL_CONST` |
| `return local;` | `RETURN_LOCAL` |
| `return a + b;` | `RETURN_ADD` |
| `self(local - const)` | `CALL_SELF_SUB_LOCAL_CONST` |
| `local < local` in a loop | `JUMP_IF_NOT_LESS_LL` |

All fusions reuse the same helpers as the general operations
(`compare_values`, `arithmetic_values`, `add_values`), so error messages and
edge-case semantics are identical. The `fib(27)` benchmark went from roughly
22 ms to roughly 13 ms with these fusions alone.

## Hot and cold dispatch

The main loop keeps hot state in local C variables:

- `ip` — the instruction pointer.
- the stack top.
- the current frame's `slots`.
- the frame's constant pool.

The hot path handles the error-free, allocation-free instructions that
dominate loops and recursion:

- constants, locals, global reads and writes;
- upvalues;
- indexing arrays and maps;
- numeric arithmetic and comparison, including pure-float and mixed
  int/float fast paths;
- fused superinstructions;
- jumps, calls (matching closures and fixed-arity natives) and returns.

On GCC and Clang, **direct threading** via computed goto eliminates a
centralized indirect jump. On other compilers the loop uses a `switch`.

Anything else — an unhandled native, an allocation, a complex string
operation, a type error, an undefined global — writes `ip` and the stack pointer
back into the VM and jumps to the general path. That writeback is what keeps
the collector and error reporting consistent.

Calls and returns have fast paths too:

- `CALL` stays hot for closures with matching arity and an available frame, and
  for native functions.
- `RETURN` stays hot unless it would leave the current `run()` (frame 0 or the
  callback base frame).
- The fast return skips `close_upvalues` when no upvalue is open.
- Each call frame caches its constant pool pointer, removing an indirection on
  return.

## Tail calls

When a `return` returns a call — including the branches of a ternary — the
compiler emits `TAIL_CALL` or `TAIL_CALL_SPREAD`. The VM:

1. closes open upvalues for the current frame;
2. copies the new arguments into the current frame's slots;
3. reinitializes the instruction pointer and constants pool;
4. executes the target function in the same frame.

Tail recursion therefore runs in O(1) frames and is not bounded by the 4096
frame limit. A tail return whose callee is a global native is compiled as an
ordinary call, because frame reuse cannot deliver a suspended network result.

## Default parameters and varargs

Functions track `min_arity` alongside `arity`. Calling with fewer arguments
than `arity` pads the stack with `nil` and records the real count. The function
preamble contains `DEFAULT_ARG slot offset` for each parameter with a default:
if the argument was supplied, it skips evaluation; otherwise it evaluates the
default expression and writes it into the local slot.

A function with `...rest` sets `is_varargs`. Arguments beyond `arity` are
collected into a new array placed in slot `arity + 1`. Spread calls and spread
array literals build and flatten an argument array with `ARRAY_PUSH` /
`ARRAY_EXTEND`, followed by `CALL_SPREAD` or `TAIL_CALL_SPREAD`.

## Constant folding and dead code

The compiler statically evaluates:

- arithmetic (`+`, `-`, `*`, `/`, `%`) and bitwise operations;
- unary operators (`-`, `!`, `~`);
- comparisons;
- string concatenation;
- ternaries and `??`.

Operations that could raise (division by zero, negative shifts) are left for
runtime so the error keeps its precise line and message. Folding also enables
superinstruction fusion when the right operand becomes a numeric constant.

Dead code after an unconditional transfer (`return`, `throw`, `break`,
`continue`) is not emitted. An `if` or `while` with a constant boolean emits
only the live branch.

## Adding an instruction

1. Add the opcode to the enum in `chunk.h`, and handle it in `opcode_name` and
   the disassembler in `chunk.c`.
2. Emit it from `compiler.c` with `emit_byte` and, for operands, `emit_u16`.
3. Implement the case in `run()` in `vm.c`, keeping the operand stack balanced
   on every path.
4. Add a fixture under `tests/cases` and document the instruction here.
5. Measure before and after with `benchmarks/run.py` if it touches a hot path.

## Next

- [Garbage Collector](@internals/garbage-collector) — how allocation and roots work.
- [Limits and Performance](@internals/limits-and-performance) — the measured numbers.
- [Bytecode and Precompilation](@tooling/bytecode) — `--dump` from the user's side.