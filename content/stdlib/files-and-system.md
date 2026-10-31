This page covers process input/output, files and directories, environment
variables, JSON, regular expressions and time. Sockets, TLS, HTTP and
WebSockets have their own section under [Networking](@networking/sockets).

## Standard input, output and arguments

| Call | Result |
| --- | --- |
| `print(a, b, ...)` | Writes the arguments, separated by spaces, plus a newline. |
| `input(prompt?)` | Reads one line from standard input without the newline; `nil` on EOF. |
| `exit(code?)` | Flushes and terminates; default code `0`. |
| `argv` | Global array: script path followed by its arguments; empty in the REPL. |

```spark
var name = input("Your name: ");
if (name == nil) {
    print("no input");
} else {
    print("hello, ${name}");
}

if (len(argv) < 2) {
    print("usage: spark script.spark FILE");
    exit(2);
}
print("file:", argv[1]);
```

`exit` bypasses `finally` blocks because it terminates the process
immediately.

## Whole-file helpers

| Call | Result |
| --- | --- |
| `read_file(path)` | Entire file contents as a string. |
| `write_file(path, data)` | Writes `data`, truncating the file. |
| `append_file(path, data)` | Appends `data` to the file. |
| `file_exists(path)` | Whether the path exists. |

```spark
var path = "/tmp/notes.txt";

write_file(path, "first\n");
append_file(path, "second\n");

print(read_file(path));
print(file_exists(path));
```

```text
first
second
```

A missing file, an unreadable path or an invalid mode raises `RuntimeError`
with a message such as `could not open '/tmp/x' for reading`. Catch it when a
missing file is expected:

```spark
fn read_or_empty(path) {
    try {
        return read_file(path);
    } catch (error) {
        return "";
    }
}
```

The whole-file helpers are the right choice for configuration files and small
documents. For streaming or line-by-line processing, use a file handle.

## File handles

| Call | Result |
| --- | --- |
| `open(path, mode?)` | Opens a handle; default mode `"r"`. |
| `read_line(file)` | Next line without its terminator; `nil` at EOF. |
| `read(file, bytes?)` | Up to `bytes` bytes, or until EOF when omitted. |
| `write(file, data)` | Writes `data`; returns the byte count. |
| `close(file)` | Closes the handle; using it afterwards is an error. |
| `eof(file)` | Whether the handle has reached end of file. |

```spark
var file = open("/tmp/log.txt", "w");
write(file, "alpha\n");
write(file, "beta\n");
close(file);

file = open("/tmp/log.txt", "r");
while (!eof(file)) {
    var line = read_line(file);
    if (line == nil) {
        break;
    }
    print(">", line);
}
close(file);
```

The usual C modes are accepted: `"r"`, `"w"`, `"a"` and their `+` variants.
Spark strings are text; binary data is not a first-class type in 0.1.0.

File handles are GC-managed: a handle that becomes unreachable is closed by the
collector. Explicit `close` is still the right habit, especially for many files
at once.

```spark
var file = open("/tmp/data.txt");
var first = read_line(file);
var rest = read(file);
file.close();          // method form
```

## Directories

```spark
print(list_dir("/tmp"));      // ["file-a.txt", "spark", ...]
mkdir("/tmp/spark-demo");     // succeeds when it already exists
```

`list_dir` returns an array of entry names (not full paths). `mkdir` creates one
directory; it does not create missing parents.

```spark
fn ensure_dir(path) {
    if (!file_exists(path)) {
        mkdir(path);
    }
}
```

## Running commands

`exec(command)` runs a shell command and returns a map:

```spark
var result = exec("printf 'hello'");
print(result.exit_code);   // 0
print(result.stdout);      // hello
print(result.stderr);      // "" (empty)
```

| Key | Meaning |
| --- | --- |
| `exit_code` | Process exit status. |
| `stdout` | Captured standard output. |
| `stderr` | Captured standard error. |

::: danger Spark is not a sandbox
`exec` can run any command the host allows. Never build a command string from
untrusted input. If you must, validate it against a strict allow-list; shell
metacharacters make escaping fragile.
:::

## Environment variables

| Call | Result |
| --- | --- |
| `env(name)` | Value as a string, or `nil` when unset. |
| `env()` | Map with every environment variable. |

```spark
var token = env("API_TOKEN");
if (token == nil) {
    print("API_TOKEN is not set");
    exit(1);
}

var all = env();
print("variable count:", len(all));
```

## Time and sleeping

| Call | Result |
| --- | --- |
| `clock()` | Monotonic seconds, for measuring elapsed time. |
| `time()` | Wall-clock seconds since the Unix epoch. |
| `sleep(ms)` | Suspends for the given number of milliseconds. |

```spark
var start = clock();
sleep(100);
print("elapsed:", clock() - start);   // approximately 0.1

print("epoch:", time());
```

Use `clock` rather than `time` for durations: the wall clock can jump.

`sleep` suspends the whole program, not just the current coroutine. Network
operations are the ones that suspend only their coroutine.

## JSON

| Call | Result |
| --- | --- |
| `to_json(value)` | JSON text for a value. |
| `from_json(text)` | Value decoded from JSON. |

```spark
var text = to_json({"name": "spark", "tags": ["fast", "small"], "ok": true});
print(text);
// {"name": "spark", "tags": ["fast", "small"], "ok": true}

var data = from_json(text);
print(data.name, data.tags[0], data.ok);   // spark fast true
```

Rules:

- Objects become maps, arrays become arrays, `null` becomes `nil`.
- Map keys are stringified in the output (`{1: "one"}` becomes `{"1": "one"}`).
- Functions, instances and other non-JSON values raise `ValueError` with
  `cannot serialize ... to JSON`.
- Malformed input raises `ValueError` with a line and column
  (`JSON parse error at line 1, column 2: ...`).
- Integers round-trip as integers when they fit; decimals become floats.
- `\uXXXX` escapes, including surrogate pairs, are decoded.

```spark
var emoji = from_json("\"\\uD83D\\uDE00\"");
print(emoji);   // 😀
```

JSON is the easiest way to persist nested collections and to talk to HTTP APIs.
See [HTTP Client](@networking/http-client) for request bodies.

## Regular expressions

| Call | Result |
| --- | --- |
| `regex_match(pattern, text)` | Whether the pattern matches anywhere in the text. |
| `regex_find(pattern, text)` | Array of all non-overlapping matches. |
| `regex_replace(pattern, replacement, text)` | Replaces every non-overlapping match. |

```spark
print(regex_match("^[a-z]+$", "spark"));       // true
print(regex_match("^[a-z]+$", "SPARK"));       // false

print(regex_find("\\d+", "item 10, item 20")); // ["10", "20"]
print(regex_replace("\\d+", "NUM", "a1b22"));  // aNUMbNUM
print(regex_replace("[aeiou]", "*", "banana"));// b*n*n*
```

Supported syntax:

| Feature | Example |
| --- | --- |
| Literals and `.` | `cat`, `a.b` |
| Character classes and ranges | `[a-z]`, `[^0-9]`, `[aeiou]` |
| Shorthand classes | `\d`, `\s`, `\w` |
| Escaped metacharacters | `\\.`, `\\+`, `\\\\` |
| Anchors | `^`, `$` |
| Quantifiers | `*`, `+`, `?` |
| Grouping | `(ab)+`, `(a|b)` |
| Alternation | `cat|dog` |

Not supported in 0.1.0: counted repetition (`{2,4}`), lazy quantifiers (`+?`),
backreferences in the replacement (`$1`), word boundaries (`\b`) and
lookaround. An invalid pattern raises `ValueError` with a regex syntax error:

```text
ValueError at line 5: regex syntax error: unexpected quantifier
```

The replacement string is inserted literally; `$1` and `\1` are not expanded.

::: tip Prefer plain string functions
For literal searches use `contains`, `index_of`, `starts_with`, `ends_with`
and `replace`. Regular expressions are for patterns, and the engine is
deliberately small.
:::

## Garbage collection

`gc()` runs a collection cycle immediately and updates the adaptive threshold:

```spark
gc();
```

Programs rarely need to call it. It is useful in benchmarks and tests that
assert memory behavior. See
[Garbage Collector](@internals/garbage-collector).

## String builder

`string_builder()` and `sb_append` / `sb_to_string` / `sb_len` / `sb_clear` are
documented in [Text](@stdlib/text#building-large-strings). They belong here in
spirit: they are the O(n) way to assemble a large text value.

## Recipes

### Reading a file line by line

```spark
fn for_each_line(path, callback) {
    var file = open(path, "r");
    try {
        while (!eof(file)) {
            var line = read_line(file);
            if (line == nil) {
                break;
            }
            callback(line);
        }
    } finally {
        close(file);
    }
}

for_each_line("/tmp/log.txt", fn(line) {
    if (contains(line, "ERROR")) {
        print(line);
    }
});
```

### Saving and loading JSON

```spark
fn save_json(path, value) {
    write_file(path, to_json(value));
}

fn load_json(path, fallback) {
    try {
        return from_json(read_file(path));
    } catch (error) {
        return fallback;
    }
}

save_json("/tmp/settings.json", {"theme": "dark", "size": 14});
var settings = load_json("/tmp/settings.json", {});
print(settings.theme);   // dark
```

::: note
0.1.0 does not expose `rename` or `remove` for files, so a genuinely atomic
write needs `exec("mv ...")` with a validated path. The roadmap tracks a
richer file API.
:::

### Timing a block

```spark
fn timed(label, work) {
    var start = clock();
    var result = work();
    print(label, "took", clock() - start, "s");
    return result;
}
```

## Next

- [Networking](@networking/sockets) — sockets and the scheduler.
- [Text](@stdlib/text) — string helpers and the builder.
- [Collections](@stdlib/collections) — JSON-friendly data structures.