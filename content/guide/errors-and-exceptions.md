Spark reports problems with categorized diagnostics, and lets a program catch
runtime failures as values.

## Diagnostics

Syntax and compilation errors are reported before anything runs:

```text
SyntaxError at line 3: expected ';' after the declaration
   3 | var x = 1
     |         ^
```

Runtime errors show the failing line, a caret and a call trace:

```text
ZeroDivisionError at line 4: division by zero
   4 |     return a / b;
     |            ^
  in divide (line 4)
  in program.spark (line 7)
```

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Successful run |
| `64` | Incorrect command-line usage |
| `65` | Syntax or compilation error |
| `70` | Runtime error |
| `74` | Could not read the file |

## Error categories

Every diagnostic starts with its category:

| Category | Raised when |
| --- | --- |
| `SyntaxError` | the source is malformed |
| `CompileError` | valid syntax but semantically wrong |
| `TypeError` | an operation receives the wrong type |
| `NameError` | a variable, method or field does not exist |
| `ConstError` | assigning to or redefining a constant at runtime |
| `ZeroDivisionError` | division or modulo by zero |
| `IndexError` | an array or string index is out of range |
| `ValueError` | a value is outside the accepted domain |
| `ArityError` | a function is called with the wrong number of arguments |
| `AssertionError` | `assert` fails |
| `RecursionError` | the call-depth limit is reached |
| `MemoryError` | an allocation fails or a result is too large |
| `NetworkError` | a socket or name-resolution failure |
| `TimeoutError` | a network operation exceeded its deadline |
| `RuntimeError` | any other runtime failure |

## throw

`throw` raises any value:

```spark
throw "something failed";
throw {"type": "ValidationError", "message": "age must be positive"};
```

Because any value can be thrown, error objects are a convention rather than a
requirement. A map with `type` and `message` keys is a useful one.

## try / catch / finally

```spark
try {
    throw {"type": "DemoError", "message": "boom"};
} catch (error) {
    print("caught:", error.type, "-", error.message);
} finally {
    print("cleanup");
}
```

```text
caught: DemoError - boom
cleanup
```

- `catch` may bind an identifier (`catch (e)`) or omit it (`catch`).
- `finally` always runs: after normal completion, after a handled exception,
  after an early `return`, and while an uncaught exception propagates.
- Only the first matching handler runs; there are no typed catch clauses.

## Catching runtime errors

Runtime errors are ordinary catchable values with `type`, `message`, `line` and
`column` keys:

```spark
try {
    var value = int("not a number");
} catch (error) {
    print(error.type);     // ValueError
    print(error.message);
    print(error.line);
}
```

This is the basis of robust I/O code: attempt the operation, and turn the
failure into a value your program understands.

```spark
fn read_config(path) {
    try {
        return from_json(read_file(path));
    } catch (error) {
        print("could not read ${path}: ${error.message}");
        return {};
    }
}
```

::: tip Only catch what you can handle
Catching every error can hide bugs. When you need to rethrow, `throw error;`
preserves the value. There is no `raise` and no typed rethrow; inspect
`error.type` if you need to discriminate.
:::

## finally in detail

`finally` also runs when the try block returns:

```spark
fn open_and_close(path) {
    var file = nil;
    try {
        file = open(path);
        return read(file);
    } finally {
        if (file != nil) {
            close(file);
        }
    }
}
```

If a `finally` block throws, that exception replaces the one being propagated.

## Uncaught exceptions

If nothing catches an exception, the VM stops with exit code `70`:

```text
RuntimeError at line 1: uncaught exception: {"message": "boom"}
   1 | throw {"message": "boom"};
     |       ^
  in program.spark (line 1)
```

The same happens for an uncaught error inside any coroutine: it aborts the
whole program, exactly as it would in the main script.

## assert

`assert(condition, message?)` raises `AssertionError` when the condition is
falsey:

```spark
assert(len(argv) >= 2, "usage: program FILE");
```

It is meant for invariants and tests, not for user-facing input validation.

## Common runtime errors

```spark
var a = [1, 2, 3];

// a[5];                   // IndexError
// 1 / 0;                  // ZeroDivisionError
// "x" + 1;                // TypeError
// undefined_name;         // NameError
// fn f(a) {} f(1, 2);     // ArityError
// assert(false);          // AssertionError
// a[1:3] = [];            // SyntaxError (a slice is not a place)
```

Some errors are deliberately precise:

- An out-of-range index names the index you wrote, not the resolved position:
  `a[-4]` on a three-element array reports `-4`.
- Assigning to a `const` after its declaration is visible is a compile error;
  the runtime `ConstError` covers functions compiled earlier.
- `int("abc")` raises `ValueError`, not `TypeError`.

## Errors and concurrency

A blocking channel operation or `yield` inside a callback raises a
`RuntimeError` instead of suspending. An uncaught error in any coroutine aborts
the program. See
[Coroutines and Channels](@guide/coroutines-and-channels).

## Next

- [Modules](@guide/modules) — sharing error helpers across files.
- [Coroutines and Channels](@guide/coroutines-and-channels) — errors across tasks.
- [Command Line and REPL](@tooling/command-line) — exit codes and the REPL's error recovery.