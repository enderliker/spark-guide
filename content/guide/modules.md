A Spark program can span several files with `import`.

```spark
import "./math_utils";
import "./helpers/strings.spark";
```

- Paths are relative to the importing file, or to the current directory in the
  REPL.
- The `.spark` extension is optional; it is appended when omitted.
- Top-level `var`, `const`, `fn` and `class` declarations in the imported file
  become available directly to the importer.
- Each module is parsed, compiled and executed **at most once** per process.
- Cyclic imports are detected and handled without re-execution or infinite
  loops.

## A two-file program

`math_utils.spark`:

```spark
const TAU = 6.283185307179586;

fn add(a, b) {
    return a + b;
}

fn square(x) {
    return x * x;
}
```

`main.spark`:

```spark
import "./math_utils";

print(add(2, 3));        // 5
print(square(7));        // 49
print(TAU);              // 6.283185307179586
```

```bash
spark main.spark
```

There is no `export` keyword and no per-module namespace. Importing is closer
to textual inclusion with execution-once semantics: the module's top level runs
in the shared global environment.

::: warning Shared global namespace
Because every module writes into the same global namespace, two files that
declare the same top-level name collide. Prefix internal helpers (`_cache`,
`math_internal_...`) or group code by feature to keep names disjoint. This is a
known 0.1.0 limitation; namespaced modules are on the
[roadmap](@appendix/roadmap).
:::

## Execution and side effects

The first `import` of a module executes its top-level statements at that point.
Later imports of the same canonical path return immediately.

```spark
// log.spark
print("log module loaded");
```

```spark
// main.spark
import "./log";
import "./log";
import "./log.spark";   // same canonical file: not executed again
```

```text
log module loaded
```

Path comparison uses the canonical path (`realpath`), so `./log`,
`./log.spark` and a symlinked path resolve to the same module.

## Modules and the REPL

In the REPL, imports resolve relative to the current working directory. Because
globals persist across lines, an imported declaration stays available for the
rest of the session.

```text
spark> import "./math_utils";
spark> add(1, 2);
3
```

## Cycles

If module A imports B and B imports A, the cycle is detected while the module
is still loading. The second import succeeds without re-executing the module,
so the names declared before the cycle are available. Write initialization code
with that in mind: do not assume the other module has finished loading.

## Modules and coroutines

An imported module runs at a deeper `run_depth`, so `yield`, a blocking channel
operation or a would-block socket call inside a module's top level raises a
`RuntimeError` instead of suspending. Do the scheduling in the script that
imports the module.

```spark
// worker.spark
fn start() {
    yield;   // RuntimeError if this is called during module loading
}
```

Functions defined in a module and called later from the main coroutine are
fine; the restriction is about suspending while the module is being loaded.

## Precompiled modules

`import` also resolves `.sparkc` bytecode files. A module can be compiled ahead
of time and imported without paying parse or compile cost. See
[Bytecode and Precompilation](@tooling/bytecode).

```bash
spark --compile math_utils.spark -o math_utils.sparkc
```

## Library layout

A practical layout for a small project:

```text
project/
  main.spark
  lib/
    config.spark
    http.spark
  data/
    settings.json
```

```spark
import "./lib/config";
import "./lib/http";

var settings = load_settings("./data/settings.json");
var server = tcp_listen(settings.host, settings.port);
http_serve(server, fn(request) {
    return {"status": 200, "body": "ok\n"};
});
```

The standard HTTP server library follows the same rule: `lib/http.spark` is
imported with a relative path, and its top-level functions become globals. See
[HTTP Server](@networking/http-server).

## Known limits

- One global namespace per process.
- No selective imports, aliases or explicit exports.
- No dynamic import expression; `import` is a statement with a string literal.
- Imported modules are executed once and cached for the lifetime of the
  process, including in the REPL.

## Next

- [Coroutines and Channels](@guide/coroutines-and-channels) — scheduling rules for modules and callbacks.
- [Bytecode and Precompilation](@tooling/bytecode) — shipping `.sparkc` modules.
- [HTTP Server](@networking/http-server) — a real module written in Spark.