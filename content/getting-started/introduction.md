Spark is a small, dynamically typed programming language with a real toolchain:
a handwritten lexer and parser, a bytecode compiler, a stack-based virtual
machine with a mark-and-sweep garbage collector, and a standard library that
covers files, JSON, regular expressions, sockets, TLS, HTTP and WebSockets.

It is implemented from scratch in C11. The only third-party dependency is
OpenSSL, linked exclusively for TLS.

::: tip New to Spark?
If you just want to see it run, jump to [Installation](@getting-started/installation)
and [Your First Program](@getting-started/first-program). Come back here for the
big picture.
:::

## A first look

```spark
class Greeter {
    init(name) {
        self.name = name;
    }

    greet() {
        return "Hello, ${self.name}!";
    }
}

var greeter = new Greeter("Spark");
print(greeter.greet());
```

```bash
$ spark hello.spark
Hello, Spark!
```

The syntax will feel familiar if you have used JavaScript or Python: braces,
`fn` for functions, `var` for mutable bindings, string interpolation with
`${...}`, and classes with `self`. What is less usual is how much is included
without a package manager.

## What makes Spark interesting

- **Two numeric types, on purpose.** Integers are exact signed 64-bit values;
  floats are IEEE doubles. Mixed arithmetic promotes, and an integer overflow
  promotes to a float instead of wrapping silently.
- **First-class functions with closures.** Functions are values, captured
  variables are shared by reference, and there are short lambdas
  (`fn(x) => x * x`), default parameters, varargs and spread calls.
- **Classes, inheritance and operator overloading.** Fields, methods, `init`,
  `extends`, `super`, statics and special methods such as `__add__` and
  `__index__`.
- **Structured error handling.** `try` / `catch` / `finally` / `throw` work
  with any value, and runtime errors are catchable too.
- **Cooperative concurrency.** `spawn`, `yield`, `join` and channels give you
  thousands of logical tasks on a single thread, with no data races.
- **Networking that respects the scheduler.** A blocking socket call suspends
  its coroutine, not the whole process, so one program serves many connections.
- **Developer tools in the box.** REPL, interactive debugger, formatter,
  linter, bytecode disassembler and precompiled `.sparkc` files.

## The implementation in one diagram

```
 .spark source
      │
      ▼
   lexer.c ── tokens ──► parser.c ── AST ──► compiler.c ── bytecode
                                                          │
                                                          ▼
                                                    vm.c (stack VM + GC)
                                                          │
                                                          ▼
                                                   result / error
```

There is no LLVM, no JIT and no generated parser. Every stage is handwritten
C, which makes the whole path readable end to end. The
[Architecture](@internals/architecture) section walks through it.

## How this guide is organized

| Section | What you will find |
| --- | --- |
| [Getting Started](@getting-started/introduction) | Build the interpreter and run your first program. |
| [Guide](@guide/variables-and-scope) | The language, from variables to coroutines. |
| [Standard Library](@stdlib/overview) | Every native function, grouped by domain. |
| [Networking](@networking/sockets) | Sockets, TLS, HTTP and WebSockets. |
| [Tooling](@tooling/command-line) | The CLI, REPL, debugger, formatter and linter. |
| [Under the Hood](@internals/architecture) | Bytecode, dispatch, garbage collection and limits. |
| [Appendix](@appendix/examples) | Example programs, project status and the roadmap. |

## Version and status

This guide documents **Spark 0.1.0**, a pre-1.0 release. The language, standard
library and toolchain are usable and covered by a large test suite, but
breaking changes are allowed before 1.0 and are recorded in the changelog.
The [roadmap](@appendix/roadmap) lists what is lined up next.

::: warning Spark is not a sandbox
`exec` and the networking natives are available to every program. Do not run
untrusted Spark code directly; use an OS-level sandbox, a container and an
egress policy. See [Files, System and Data](@stdlib/files-and-system) and
[Networking](@networking/sockets) for the details.
:::

## Conventions used here

- Code you can run appears in `spark` blocks. Shell commands use `bash`.
- `print(...)` output is shown in comments: `print(1 + 2); // 3`.
- The notation `fn f(a, b = 1)` means parameter `b` has a default value.
- Exit codes and error categories are reproduced exactly as the interpreter
  reports them.
- `>>>` in a block would mark REPL input; ordinary programs use files.

Ready? [Install Spark](@getting-started/installation).