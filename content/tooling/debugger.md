`spark --debug file.spark` runs a program under an interactive debugger.

```bash
spark --debug script.spark
```

```text
Spark Debugger. Type 'help' for commands, 'continue' or 'c' to run.
Stopped at /tmp/dbg.spark:1
-> 1 | fn divide(a, b) {
(dbg)
```

The debugger stops at the first source line and waits for a command. Outside
`--debug` it costs nothing: normal execution never checks breakpoints.

## Commands

| Command | Alias | Effect |
| --- | --- | --- |
| `break <[file:]line>` | `b` | Set a breakpoint at a source line or `file:line`. |
| `delete <id>` | `d` | Delete a breakpoint by number. |
| `list` | | List active breakpoints. |
| `step` | `s` | Step into the next source line. |
| `next` | `n` | Step over the next line (skip calls). |
| `continue` | `c` | Run until the next breakpoint or program end. |
| `locals` | `l` | Show local variables in the current frame. |
| `stack` | `bt` | Print the call stack. |
| `help` | `h` | Show the command list. |
| `quit` | `q` | Terminate immediately. |

## A session

Given `dbg.spark`:

```spark
fn divide(a, b) {
    var result = a / b;
    return result;
}

var x = 10;
var y = 2;
print(divide(x, y));
```

```text
$ spark --debug dbg.spark
Spark Debugger. Type 'help' for commands, 'continue' or 'c' to run.
Stopped at dbg.spark:1
-> 1 | fn divide(a, b) {
(dbg) break 2
Breakpoint 1 set at 2
(dbg) continue
Breakpoint 1 hit at dbg.spark:2
-> 2 |     var result = a / b;
(dbg) locals
Locals:
  a = 10
  b = 2
(dbg) stack
Call stack:
  #1 divide() at dbg.spark:2
  #0 dbg.spark() at dbg.spark:8
(dbg) next
Stopped at dbg.spark:3
-> 3 |     return result;
(dbg) locals
Locals:
  a = 10
  b = 2
  result = 5
(dbg) continue
5
```

Use `file:line` when a program spans modules and the same line number exists in
more than one file:

```text
(dbg) break lib/http.spark:120
```

## Breakpoint management

```text
(dbg) break 12
Breakpoint 2 set at 12
(dbg) break lib/http.spark:40
Breakpoint 3 set at lib/http.spark:40
(dbg) list
Breakpoints:
  #1: <any>:2 [enabled]
  #2: <any>:12 [enabled]
  #3: lib/http.spark:40 [enabled]
(dbg) delete 2
Breakpoint 2 deleted
```

Breakpoints set without a file show `<any>`, which matches the line in any
file. Breakpoint numbers are assigned in creation order and are stable until
deleted. Setting a breakpoint on a line with no executable instruction is
accepted; it fires when execution reaches that source line.

## Inspecting state

`locals` prints the current frame's locals as `name = value`, including
parameters and temporaries that have been initialized. Names come from the
compiler's debug metadata, so they match the source.

`stack` prints frames from innermost to outermost with the function name and
source line:

```text
Call stack:
  #1 divide() at dbg.spark:2
  #0 dbg.spark() at dbg.spark:8
```

The top frame is `#1`; the script frame is `#0`.

## Stepping

- `step` enters function calls.
- `next` runs the current line and stops at the next line in the same frame,
  stepping over calls.
- `continue` resumes until a breakpoint or the end of the program.

Stepping is line-based, using the same line table that powers runtime error
traces, so every stopped location maps back to a real source line.

## Practical tips

- Set a breakpoint before `continue`; the debugger starts stopped at line 1.
- Use `next` on a line that calls a suspicious function to see whether it
  returns, then `step` into it on the next run.
- `quit` terminates immediately, without running `finally` blocks.
- The debugger and the regular VM share the same semantics; stepping does not
  change evaluation order or values.

## Relationship to error traces

Runtime errors already carry a trace:

```text
ZeroDivisionError at line 2: division by zero
   2 |     return a / b;
     |              ^
  in divide (line 2)
  in program.spark (line 8)
```

Use the debugger when you need values and control flow, and the trace when you
just need to know where it failed.

## Next

- [Formatter and Linter](@tooling/formatter-and-linter) — static checks before running.
- [Bytecode and Precompilation](@tooling/bytecode) — what the debugger is stepping through.
- [Errors and Exceptions](@guide/errors-and-exceptions) — traces and error values.