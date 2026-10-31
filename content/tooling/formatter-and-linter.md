Spark ships with a canonical formatter and a static linter. Neither has a
configuration file: the formatting rules and the lint rules are fixed, which
keeps diffs small and automation simple.

## Formatter

```bash
spark --format file.spark       # canonical source to stdout
spark --format -w file.spark    # rewrite the file in place
```

Given:

```spark
var  x=1+2;
fn f(a,b){if(a>b){return a;}else{return b;}}
var m={"a":1};
print(m["a"]+x);
```

`spark --format` produces:

```spark
var x = 1 + 2;
fn f(a, b) {if (a > b) {
        return a;
    } else {
        return b;
    }
}
var m = {"a": 1};
print(m["a"] + x);
```

::: note
The formatter normalizes spacing, indentation and brace layout; comments and
string interpolations are preserved verbatim. It does not reorder or rewrite
expressions, so formatting never changes behavior.
:::

### Rules

- Indentation: four spaces per nesting level.
- Semicolons followed by a newline, except in `for` headers.
- Binary and assignment operators surrounded by spaces.
- Commas followed by a single space.
- Comments (`//` and `/* ... */`) and string interpolations preserved verbatim.
- Idempotent: formatting twice produces byte-identical output.

Idempotence is verified by the test suite and makes `--format -w` safe in a
pre-commit hook. Running it twice leaves the second run with nothing to change:

```bash
spark --format -w src/*.spark
spark --format -w src/*.spark   # no diff
```

The formatter parses the file first, so a syntax error is reported instead of
producing partial output.

## Linter

```bash
spark --lint file.spark
```

The linter performs a single-pass AST analysis and reports three rules:

| Rule | What it reports |
| --- | --- |
| `unused-variable` | A local variable or parameter is declared but never referenced. |
| `unreachable-code` | A statement follows `return`, `throw`, `break` or `continue` in the same block. |
| `shadowed-variable` | An inner declaration shadows an enclosing local or parameter. |

Names beginning with `_` are intentionally ignored by the unused-variable
check:

```spark
fn handle(_event, value) {
    return value;
}
```

### Output format

```text
file.spark:3:6: warning [shadowed-variable]: variable 'a' shadows variable declared at line 1
file.spark:5:2: warning [unreachable-code]: unreachable code after 'return'
file.spark:2:6: warning [unused-variable]: variable 'unused' is declared but never used
file.spark:1:4: warning [unused-variable]: variable 'a' is declared but never used
```

Each line is `path:line:column: warning [rule]: message`.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No findings. |
| `1` | At least one warning. |
| `65` | Syntax error. |
| `74` | The file could not be read. |

That makes the linter a drop-in CI gate:

```bash
spark --lint src/main.spark || exit 1
```

### What it does not check

The linter is deliberately small. It does not perform type checking, it does
not detect unreachable code across jumps or into nested blocks in every case,
and it does not flag unused globals or unused functions. It is a fast sanity
check, not a proof of correctness.

## Using both in CI

```bash
#!/bin/sh
set -eu

for file in "$@"; do
    spark --format "$file" > /dev/null
done

spark --lint "$@"
```

Formatting validation catches unformatted edits; linting catches dead code and
accidental shadowing. Both run on syntax validation first, so a broken file
fails early with exit code `65`.

## Next

- [Debugger](@tooling/debugger) — runtime inspection.
- [Command Line and REPL](@tooling/command-line) — the full CLI surface.
- [Bytecode and Precompilation](@tooling/bytecode) — inspecting what the compiler emitted.