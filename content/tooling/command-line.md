The `spark` binary runs programs, opens a REPL and drives the built-in tools.

```text
Spark 0.1.0 - an interpreted programming language with a virtual machine.

Usage: spark [options] [file.spark | file.sparkc]

Options:
  --compile <file>  compile source to bytecode file (.sparkc)
  -o <output>       output file for --compile (defaults to <file>.sparkc)
  --debug           run file with interactive debugger
  --dump            compile and show the bytecode without running
  --format <file>   format source file to canonical style
  -w, --write       write formatted output in-place (with --format)
  --lint <file>     report unused variables, unreachable code and shadowing
  --help            show this help
  --version         show the version

Without a file an interactive REPL opens. Type 'exit' to exit.
```

## Options

| Option | Effect |
| --- | --- |
| `--compile <file>` | Compiles source to `<file>.sparkc`. |
| `-o <output>` | Sets the output path for `--compile`. |
| `--dump` | Prints the bytecode and exits without running. |
| `--debug` | Runs the file under the interactive debugger. |
| `--format <file>` | Prints canonical formatting to stdout. |
| `-w`, `--write` | With `--format`, rewrites the file in place. |
| `--lint <file>` | Static analysis; exit code 1 when there are warnings. |
| `--help` | Prints usage. |
| `--version` | Prints `Spark 0.1.0`. |

```bash
spark program.spark
spark program.sparkc
spark --dump program.spark
spark --compile program.spark -o program.sparkc
spark --debug program.spark
spark --format program.spark
spark --format -w program.spark
spark --lint program.spark
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `64` | Incorrect command-line usage. |
| `65` | Syntax or compilation error. |
| `70` | Runtime error. |
| `74` | The file could not be read. |

The linter is the exception: it returns `1` when it reports findings, `0` when
clean, `65` on a syntax error and `74` when the file cannot be read.

```bash
spark program.spark
echo $?          # 0, 65, 70 or 74
```

## Script arguments

Arguments after the file name become `argv[1]`, `argv[2]`, ...; `argv[0]` is
the script path.

```bash
spark tool.spark input.txt --fast
```

```spark
print(argv[0]);   // tool.spark
print(argv[1]);   // input.txt
print(argv[2]);   // --fast
```

In the REPL, `argv` is an empty array.

## The REPL

Run `spark` with no arguments:

```text
Spark 0.1.0 — type code and press Enter. 'exit' or Ctrl+D to exit.
spark>
```

- Every standalone expression prints its value.
- Global variables persist between lines.
- `_` holds the result of the last expression statement.
- Errors are reported and the session continues.
- Lines accumulate while braces are unclosed, so multi-line functions work.
- `exit`, `quit` or Ctrl+D ends the session.

```text
spark> 1 + 2;
3
spark> var greeting = "hello";
spark> greeting + ", world";
hello, world
spark> _;
hello, world
spark> fn double(x) {
 ...     return x * 2;
 ... }
spark> double(21);
42
spark> exit
```

::: warning Statements need semicolons
The REPL follows the language grammar: `1 + 2;` prints `3`, while `1 + 2`
without the semicolon is a `SyntaxError`. The prompt continues with `...` until
the statement is complete.
:::

The REPL compiles each entry in a special mode that turns expression
statements into a print instruction. Globals survive across entries, so modules
imported once stay available.

## Running precompiled files

`spark` runs `.sparkc` bytecode directly, with no parsing or compilation:

```bash
spark --compile server.spark
spark server.sparkc
```

A `.sparkc` file can also be imported by another module. See
[Bytecode and Precompilation](@tooling/bytecode).

## Choosing the input

The interpreter decides by the file argument, not by the extension alone:

- A `.sparkc` file is loaded as precompiled bytecode.
- Any other path is read as Spark source.

If the file cannot be read, the exit code is `74`.

## Reproducible tooling

The formatter and linter are designed for automation:

```bash
spark --format -w src/*.spark
spark --lint src/*.spark || exit 1
```

`--format` is idempotent, so it is safe to run in a pre-commit hook.
`--lint` returns `1` for findings, which makes it usable as a CI gate without
parsing output. See [Formatter and Linter](@tooling/formatter-and-linter).

## Next

- [Debugger](@tooling/debugger) — breakpoints and stepping.
- [Bytecode and Precompilation](@tooling/bytecode) — `--dump` and `.sparkc`.
- [Architecture](@internals/architecture) — what happens after the file is read.