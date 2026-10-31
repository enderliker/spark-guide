Spark compiles source to bytecode before running it. Two flags expose that
stage: `--dump` prints the bytecode, and `--compile` writes it to a `.sparkc`
file.

## Inspecting bytecode

```bash
spark --dump program.spark
```

```spark
fn add(a, b) {
    return a + b;
}
print(add(1, 2));
```

```text
== program.spark ==
0000    1 CLOSURE               0 '<fn add>'
0003    | DEFINE_GLOBAL       122 'add'
0006    4 GET_GLOBAL            0 'print'
0009    | GET_GLOBAL          122 'add'
0012    | CONSTANT              1 '1'
0015    | CONSTANT              2 '2'
0018    | CALL                  2
0020    | CALL                  1
0022    | POP
0023    1 NIL
0024    | RETURN

== add ==
0000    2 GET_LOCAL             1
0002    | GET_LOCAL             2
0004    | RETURN_ADD
0005    1 NIL
0006    | RETURN
```

Columns:

| Column | Meaning |
| --- | --- |
| Offset | Byte offset into the function's `code[]`. |
| Line | Source line that produced the instruction. A `\|` means "same line as above". |
| Instruction | Opcode name. |
| Operand | Constant index, slot, jump target or argument count. |
| Annotation | Constant value or target name, when applicable. |

The dump follows the program's structure: one `== name ==` block per function,
starting with the script.

## Reading a loop

```spark
var total = 0;
for (var i = 0; i < 3; i += 1) {
    total += i;
}
print(total);
```

```text
== program.spark ==
0000    1 CONSTANT              0 '0'
0003    | DEFINE_GLOBAL       122 'total'
0006    2 CONSTANT              0 '0'
0009    | JUMP_IF_NOT_LESS_LC    1 '3' -> 33
0015    3 GET_GLOBAL          122 'total'
0018    | GET_LOCAL             1
0020    | ADD
0021    | SET_GLOBAL          122 'total'
0024    2 ADD_LOCAL_CONST       1 '1'
0028    | SET_LOCAL             1
0030    | LOOP                 30 -> 9
0033    | POP
0034    5 GET_GLOBAL            0 'print'
0037    | GET_GLOBAL          122 'total'
0040    | CALL                  1
0042    | POP
0043    1 NIL
0044    | RETURN
```

Things worth noticing:

- `CONSTANT 0 '0'` is reused; the constant pool deduplicates values.
- `JUMP_IF_NOT_LESS_LC` compares the local `i` with the constant `3` and
  branches without materializing a boolean. It is a fused superinstruction.
- `ADD_LOCAL_CONST` fuses `i + 1`.
- `LOOP 30 -> 9` jumps backwards to the loop condition.
- Globals are addressed by slot (`122`), not by hashing a name at runtime.

The [Bytecode and Dispatch](@internals/bytecode-and-dispatch) page covers the
instruction set and the fusion rules in depth.

## Compiling to `.sparkc`

```bash
spark --compile script.spark              # writes script.sparkc
spark --compile script.spark -o out.sparkc
spark script.sparkc                       # runs it directly
```

A `.sparkc` file:

- starts with the 4-byte magic `SPRK` and a binary format version;
- stores the active global names so slot mappings survive across modules;
- serializes bytecode, line/column tables and constants, including nested
  functions and closures;
- loads and runs without invoking the lexer or the parser.

```bash
ls -l script.spark script.sparkc
spark script.sparkc
```

::: warning Bytecode is version-specific
The format carries a version number. A `.sparkc` file produced by a different
interpreter version may be rejected. Recompile after upgrading Spark; do not
ship bytecode as a long-lived artifact unless you pin the interpreter.
:::

## Importing precompiled modules

`import` resolves `.sparkc` files too:

```spark
import "./lib/math_utils";        // resolves math_utils.spark or .sparkc
```

```bash
spark --compile lib/math_utils.spark -o lib/math_utils.sparkc
spark main.spark
```

This lets you distribute a library without source while keeping the same
import statement. The module cache and cycle detection work identically.

## What is not in the dump

`--dump` prints the compiled script and exits; it does not run the program and
does not print the constants' full objects. Functions appear as
`<fn name>`; the string bodies of constants are shown with quotes.

## When to use it

- Diagnose why a hot loop is slow: look for fused instructions and global
  versus local access.
- Confirm constant folding: `print(1 + 2);` should show a folded constant.
- Check tail calls: a `return f(x);` should emit `TAIL_CALL`, not `CALL`.
- Verify that a construct compiles to what you expect before optimizing.

```spark
print(1 + 2);
```

```text
0000    1 GET_GLOBAL            0 'print'
0003    | CONSTANT              0 '3'
0006    | CALL                  1
0008    | POP
0009    | NIL
0010    | RETURN
```

The addition is gone: the compiler folded it.

## Next

- [Bytecode and Dispatch](@internals/bytecode-and-dispatch) — how the VM executes these instructions.
- [Architecture](@internals/architecture) — the full pipeline.
- [Command Line and REPL](@tooling/command-line) — every flag.