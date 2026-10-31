Create a file named `hello.spark`:

```spark
// hello.spark — our first Spark program
print("Hello, Spark!");
```

Run it:

```bash
spark hello.spark
```

```text
Hello, Spark!
```

That is the whole ceremony: no `main`, no imports, no build step. Top-level
statements execute in order.

## A slightly bigger program

Let us compute Fibonacci numbers and print them with interpolation:

```spark
fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

for (var i = 0; i < 10; i += 1) {
    print("fib(${i}) =", fib(i));
}
```

```text
fib(0) = 0
fib(1) = 1
fib(2) = 1
fib(3) = 2
fib(4) = 3
fib(5) = 5
fib(6) = 8
fib(7) = 13
fib(8) = 21
fib(9) = 34
```

Take it apart:

- `//` starts a line comment. `/* ... */` is a block comment and can nest.
- `fn fib(n) { ... }` declares a function. A function without `return`
  returns `nil`.
- `if (n < 2)` runs the block when the condition is truthy. `nil` and `false`
  are the only falsey values.
- `return fib(n - 1) + fib(n - 2);` recurses. This call is in tail position
  only for the second half of the expression, so it uses ordinary stack frames.
- `for (var i = 0; i < 10; i += 1)` is the C-style loop. `i += 1` is a
  compound assignment; `i++` exists too.
- `"fib(${i}) =", fib(i)` passes two arguments to `print`. The string
  interpolates `i`; the second argument is converted to text by `print` itself.

## The same program with a class

Spark classes are small: fields, methods, `init` and `new`.

```spark
class Counter {
    var total = 0;

    add(value) {
        self.total += value;
        return self;
    }

    report() {
        return "total = ${self.total}";
    }
}

var counter = new Counter();
counter.add(10).add(5);
print(counter.report());   // total = 15
```

`add` returns `self`, so calls chain. `self` is bound automatically on a method
call. See [Classes and Objects](@guide/classes-and-objects) for inheritance,
statics and operator overloading.

## Handling an error

Errors are values, so `catch` can inspect them like any other map:

```spark
try {
    throw {"type": "DemoError", "message": "something went wrong"};
} catch (error) {
    print("caught:", error.type, "-", error.message);
} finally {
    print("cleanup always runs");
}
```

Runtime errors carry `type`, `message`, `line` and `column` too. You can catch
them with the same syntax. The complete category list is in
[Errors and Exceptions](@guide/errors-and-exceptions).

## What an error looks like

A syntax error is reported before anything runs:

```text
SyntaxError at line 2: expected ';' after the declaration
   2 |
     | ^
```

A runtime error shows the source line and a call trace:

```text
ZeroDivisionError at line 2: division by zero
   2 |     return a / b;
     |              ^
  in divide (line 2)
  in program.spark (line 4)
```

The interpreter exits with code `65` for syntax or compilation errors and `70`
for runtime errors. Exit code `0` means success, `64` is a CLI usage error and
`74` means the file could not be read.

## Try things in the REPL

```bash
spark
```

```text
Spark 0.1.0 — type code and press Enter. 'exit' or Ctrl+D to exit.
spark> var greeting = "hello";
spark> greeting + ", world";
hello, world
spark> [1, 2, 3].map(fn(x) => x * x);
[1, 4, 9]
spark> exit
```

Standalone expressions print their value, globals persist between lines, and
the last result is stored in `_`. Statements still need their semicolon. Lines
with unclosed braces continue on the next line, so multi-line functions work.

::: tip Semicolons matter
Unlike JavaScript, Spark does not insert semicolons automatically. Every
statement ends with `;`. The REPL follows the same rule.
:::

## Where to go next

- [Variables and Scope](@guide/variables-and-scope) — bindings, constants and blocks.
- [Types and Values](@guide/types-and-values) — the value model in detail.
- [Functions and Closures](@guide/functions-and-closures) — Spark's functional side.
- [Example Gallery](@appendix/examples) — larger, runnable programs.