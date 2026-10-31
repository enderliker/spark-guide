This page covers process input/output, files and directories, binary data,
codecs, compression, environment variables, time, JSON, regular expressions and
cryptography. Sockets, TLS, HTTP and WebSockets have their own section under
[Networking](@networking/sockets).

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
| `read_bytes(path, max?)` | Entire file contents as `bytes`. |
| `write_bytes(path, data)` | Writes `bytes`, truncating the file. |
| `append_bytes(path, data)` | Appends `bytes` to the file. |
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

## Binary files

The `*_bytes` helpers move raw bytes without a text detour, so a file that is
not valid UTF-8 survives the round trip:

```spark
var data = bytes_from([0x00, 0x01, 0xff, 0x41]);

write_bytes("/tmp/blob.bin", data);
append_bytes("/tmp/blob.bin", bytes_from("AB"));

var back = read_bytes("/tmp/blob.bin");
print(type(back), len(back));            // bytes 6
print(bytes_to_array(back));             // [0, 1, 255, 65, 65, 66]
```

`read_bytes` refuses to truncate: a file larger than `max` raises `ValueError`
instead of returning its first `max` bytes. The default cap is 16 MiB, and
`max` may only lower it, so a mislabeled file cannot exhaust memory:

```spark
write_file("/tmp/text.txt", "héllo\n");

try {
    read_bytes("/tmp/text.txt", 3);
} catch (error) {
    print(error.type);   // ValueError — the file exceeds the 3-byte limit
}
```

Use `read_bytes` even for text when you care about the exact encoding — `héllo`
is 5 characters but 7 bytes with its newline:

```spark
var raw = read_bytes("/tmp/text.txt");
print(len(raw), to_string(raw) == "héllo\n");   // 7 true
```

## Bytes and codecs

A `bytes` value is an immutable sequence of byte values. It is built at run
time — there is no literal — and it never converts to or from `string`
implicitly. The [Types and Values](@guide/types-and-values#bytes-are-binary-values)
guide covers indexing, slicing, equality and the `+` operator; the natives are:

| Call | Result |
| --- | --- |
| `bytes(n)` | `n` zero bytes; a negative `n` is a `ValueError`. |
| `bytes_from(x)` | From an array of integers in `0..255`, or from a string's UTF-8 bytes. |
| `to_string(b)` | The text the bytes encode; invalid UTF-8 is a `ValueError` naming the offset. |
| `to_bytes(s)` | The string's UTF-8 bytes, unchanged. |
| `bytes_to_array(b)` | One integer in `0..255` per byte. |

```spark
print(bytes(3));                              // b"\x00\x00\x00"
print(bytes_from([0xff, 0x41]));              // b"\xffA"
print(bytes_to_array(bytes_from("A")));       // [65]
print(to_string(to_bytes("héllo")));          // héllo
```

`base64_encode` and `hex_encode` accept `bytes` or a string (whose UTF-8 bytes
are encoded as they are) and return `bytes`; the decoders accept either type
and return `bytes`. Decoding validates its input instead of guessing:

```spark
print(base64_encode("hi"));            // b"aGk="
print(hex_encode("hi"));               // b"6869"
print(to_string(base64_decode("aGk=")));   // hi
print(to_string(hex_decode("6869")));      // hi
```

- `base64_decode` accepts standard base64 with or without padding; a bad
  character, a truncated group or misplaced padding is a `ValueError`.
- `hex_decode` accepts either case; an odd length or a bad digit is a
  `ValueError`.
- Neither decoder is lenient: whitespace and line breaks must be removed first.

For repeated appends, `bytes_builder()` is the mutable companion of
`string_builder()`. `append` takes a byte value or `bytes` — not text:

```spark
var b = bytes_builder();
b.append(72).append(bytes_from("i"));
print(b, b.len(), b.to_bytes());   // b"Hi" 2 b"Hi"
b.clear();
print(b.len());                    // 0
```

The function forms `bb_append`, `bb_to_bytes`, `bb_len` and `bb_clear` are
equivalent to the methods.

## Compression

`inflate` decodes a raw DEFLATE stream (RFC 1951) and `gunzip` a complete gzip
member (RFC 1952). Both take `bytes` or a string and return `bytes`:

```spark
var page = gunzip(read_bytes("page.html.gz"));
print(to_string(page));

var payload = inflate(read_bytes("payload.deflate"));
```

- `gunzip` verifies the header, the trailing CRC-32 and the uncompressed size,
  so a corruption anywhere in the member is reported rather than returning
  wrong bytes. `inflate` has no trailer to verify, but a truncated stream fails
  while it is being decoded.
- Both cap the output at **16 MiB**; a second argument may lower that limit but
  not raise it. A malformed stream, a checksum mismatch, data that is not gzip
  or output beyond the cap is a `ValueError`, so a decompression bomb fails
  instead of exhausting memory.
- Only the first gzip member is decoded and trailing data is ignored. There is
  no compressor and no zlib (RFC 1950) wrapper in 0.1.0.

```spark
// Lower the cap when the input is untrusted; a larger output is a ValueError.
var small = gunzip(read_bytes("untrusted.gz"), 1024);
```

::: warning Validate everything you decompress
A gzip stream carries no trust signal. Decompress untrusted input with an
explicit, small `max`, and validate the decoded bytes before parsing them.
:::

## File handles

| Call | Result |
| --- | --- |
| `open(path, mode?)` | Opens a handle; default mode `"r"`. |
| `read_line(file)` | Next line without its terminator; `nil` at EOF. |
| `read(file, bytes?)` | Up to `bytes` bytes, or until EOF when omitted; `bytes` when the mode has a `b`. |
| `write(file, data)` | Writes a string or `bytes`; returns the byte count. |
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

The usual C modes are accepted: `"r"`, `"w"`, `"a"` and their `+` variants, and
a `b` in the mode switches the handle to binary. A binary handle returns
`bytes` from `read`, while `read_line` always returns a string and `write`
accepts either type on any handle:

```spark
var file = open("/tmp/blob-out.bin", "wb");
print(write(file, bytes_from([1, 2, 3])));   // 3
close(file);

file = open("/tmp/blob-out.bin", "rb");
var chunk = read(file, 2);
print(type(chunk), bytes_to_array(chunk));   // bytes [1, 2]
close(file);
```

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
| `time_ms()` | Wall-clock milliseconds since the Unix epoch. |
| `sleep(ms)` | Suspends for the given number of milliseconds. |

```spark
var start = clock();
sleep(100);
print("elapsed:", clock() - start);   // approximately 0.1

print("epoch:", time());
print("epoch ms:", time_ms());
```

Use `clock` rather than `time` for durations: the wall clock can jump.
`time_ms` is the millisecond counterpart of `time`, useful for log timestamps.

`sleep` suspends the whole program, not just the current coroutine. Network
operations are the ones that suspend only their coroutine.

## Dates and times

Timestamps are Unix seconds. `time_format` and `time_parse` are **UTC by
default**, so output does not depend on the host's zone; a third argument
selects the local zone explicitly.

| Call | Result |
| --- | --- |
| `time_format(timestamp?, format, local?)` | Formats the timestamp (default: now). |
| `time_parse(text, format, local?)` | Unix seconds parsed in UTC, or in the local zone when `local` is true. |
| `time_utc(timestamp)` | The UTC offset in seconds, always `0`. |
| `time_local(timestamp)` | The host's offset from UTC at that instant, in seconds (positive east of Greenwich). |

```spark
var t = time_parse("2024-02-29 12:34:56", "%Y-%m-%d %H:%M:%S");
print(t);                                                    // 1709210096
print(time_format(t, "%a %d %b %Y %H:%M:%S %z"));            // Thu 29 Feb 2024 12:34:56 +0000
print(time_format(t, "%Y-%m-%d %H:%M", true));               // host-local rendering
print(time_utc(t), time_local(t));                           // 0 and the host offset
```

Directives: `%Y` (0001..9999), `%m`, `%d`, `%H`, `%M`, `%S`, `%j` (day of year),
`%w` (weekday, Sunday is `0`), `%a`/`%A` (short/long weekday), `%b`/`%B`
(short/long month), `%z` (`+0300`), `%Z` (zone name) and `%%`.

- Month and weekday names are always English: the formatter never consults the
  locale, so output is the same on every machine.
- In a parse pattern `%b`/`%B` accept the English names in either case, `%a`/`%A`
  accept a weekday name and ignore it, `%w` is parsed and ignored, and an
  explicit `%z` overrides the `local` flag.
- Fields missing from the pattern default to the epoch's date and midnight:
  `time_parse("2024", "%Y")` is 2024-01-01T00:00:00Z.
- The range is 0001-01-01T00:00:00Z to 9999-12-31T23:59:59Z. Text that does not
  match the pattern, an unknown directive and an out-of-range field are
  `ValueError`s.

## JSON

| Call | Result |
| --- | --- |
| `to_json(value)` | JSON text for a value. |
| `from_json(text)` | Value decoded from JSON. |

```spark
var text = to_json({"name": "spark", "tags": ["fast", "small"], "ok": true});
print(text);
// {"tags": ["fast", "small"], "name": "spark", "ok": true}

var data = from_json(text);
print(data.name, data.tags[0], data.ok);   // spark fast true
```

The key order above is the map's internal order, not the insertion order; JSON
does not promise that keys come back in any particular sequence.

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

`bytes` has no native JSON form, so `to_json` writes it as a marked object with
a base64 payload. `from_json` returns that map as written — decode it explicitly:

```spark
var blob = bytes_from([0x00, 0x01, 0xff, 0x41, 0x41, 0x42]);
var encoded = to_json(blob);
print(encoded);                     // {"$bytes":"AAH/QUFC"}

var decoded = from_json(encoded);
print(base64_decode(decoded["$bytes"]));   // b"\x00\x01\xffAAB"
```

JSON is the easiest way to persist nested collections and to talk to HTTP APIs.
See [HTTP Client](@networking/http-client) for request bodies.

## Regular expressions

| Call | Result |
| --- | --- |
| `regex_match(pattern, text, flags?)` | Whether the pattern matches anywhere in the text. |
| `regex_find(pattern, text, flags?)` | Array of all non-overlapping matches. |
| `regex_find_index(pattern, text, flags?)` | The same matches as `{start, end}` maps with character offsets. |
| `regex_match_at(pattern, text, start, flags?)` | A match starting exactly at `start`, as `{start, end}`, or `nil`. |
| `regex_match_groups(pattern, text, flags?)` | The first match with its captures, or `nil`. |
| `regex_replace(pattern, template, text, flags?)` | Replaces every match, expanding `$0`, `$1`, `${name}` and `$$`. |
| `regex_split(pattern, text, limit?, flags?)` | The fields between pattern separators. |

```spark
print(regex_match("^[a-z]+$", "spark"));       // true
print(regex_match("^[a-z]+$", "SPARK"));       // false

print(regex_find("\\d+", "item 10, item 20")); // ["10", "20"]
print(regex_replace("\\d+", "NUM", "a1b22"));  // aNUMbNUM
print(regex_replace("[aeiou]", "*", "banana"));// b*n*n*
print(regex_find_index("\\d+", "ab12cd345"));  // [{start:2,end:4}, {start:6,end:9}]
```

The engine is the same one Perl and JavaScript describe: **leftmost-first**.
The match that starts earliest wins, and among alternatives the first one
written wins. Quantifiers are greedy unless suffixed with `?`.

| Feature | Example |
| --- | --- |
| Literals and `.` (not `\n` unless the `s` flag) | `cat`, `a.b` |
| Character classes and ranges | `[a-z]`, `[^0-9]`, `[aeiou]` |
| Shorthand classes | `\d`, `\s`, `\w` and their negations |
| Escaped metacharacters | `\\.`, `\\+`, `\\\\` |
| Anchors | `^`, `$` |
| Quantifiers | `*`, `+`, `?`, `{2,4}`, `{3,}` |
| Lazy quantifiers | `*?`, `+?`, `??`, `{2,4}?` |
| Groups | `(ab)+`, `(?:ab)`, `(?P<name>ab)` |
| Alternation | `cat|dog` |
| Inline flags | `(?i)abc` |

```spark
print(regex_find("a{2,3}", "aaaaa"));   // ["aaa", "aa"]
print(regex_find("<.*?>", "<a><b>"));   // ["<a>", "<b>"] — lazy
print(regex_match("ABC", "abc", "i"));  // true — case-insensitive
```

The flags argument is a string with any of `i` (case-insensitive), `s` (`.` also
matches a newline) and `m` (`^` and `$` also match at line boundaries); an
unknown flag is a `ValueError`. Case folding covers ASCII letters only.

Not supported: lookaround, `\b` word boundaries and backreferences. An escaped
ordinary character is that character, so `(a)\1` means `a` followed by `1`, and
`\b` means `b`. An invalid pattern raises `ValueError` with a syntax error:

```text
ValueError at line 5: regex syntax error: unclosed parenthesis
```

The engine is bounded so that a crafted pattern cannot hang the interpreter:
1024 instructions, 32 capture groups, a repetition count of at most 10,000, and
20,000,000 steps per call. Exceeding one is a `ValueError`.

### Capture groups

`regex_match_groups` returns the first match with every capture, or `nil`:

```spark
var m = regex_match_groups("(?P<year>\\d{4})-(?P<month>\\d{2})-(?P<day>\\d{2})",
                           "release 2026-10-31");
print(m["start"], m["end"]);          // 8 18, the whole match
print(len(m["groups"]));              // 3
print(m["groups"][0]["text"]);        // 2026
print(m["named"]["month"]["text"]);   // 10
```

| Field | Meaning |
| --- | --- |
| `start`, `end` | Character offsets of the whole match. |
| `groups` | Maps `{start, end, text}`, one per capturing group in opening-parenthesis order. |
| `named` | Map from `(?P<name>...)` to the same group map. |

A group that did not participate is `nil` in both `groups` and `named`, and a
group repeated by a quantifier keeps its **last** match, as in Perl. All
offsets are character offsets, even after multibyte text.

### Replacement templates

`regex_replace` expands groups in the template:

| Template | Expands to |
| --- | --- |
| `$0` | The whole match. |
| `$1` ... `$32` | A numbered group. |
| `${name}` | A named group. |
| `$$` | A literal `$`. |

```spark
print(regex_replace("(\\w+)@(\\w+)", "$2.$1", "user@host"));   // host.user
print(regex_replace("(?P<a>\\d)", "<$${a}>", "1-2"));          // <1>-<2>
```

A group that did not participate expands to nothing, and a `$` not followed by
a digit, `{` or `$` is literal. The template is validated before matching, so an
unknown group is an error even when the pattern never matches. In a Spark string
literal write `$${name}` for `${name}`, because `${...}` is interpolation.

### Splitting on a pattern

`regex_split` returns the fields between separators:

```spark
print(regex_split("\\s+", "one  two\tthree"));   // ["one", "two", "three"]
print(regex_split(",", ",a,,b,"));               // ["", "a", "", "b", ""]
print(regex_split("ABC", "xabcx", "i"));         // ["x", "x"]
```

Unlike Python's `re.split`, groups in the separator do not add fields. Leading,
trailing and doubled separators produce empty fields, and `limit` behaves as it
does in `split`: the maximum field count, `0` returns `[]`, and the last field
keeps the remainder.

::: tip Prefer plain string functions
For literal searches use `contains`, `index_of`, `starts_with`, `ends_with`,
`count` and `replace`. Regular expressions are for patterns, and the engine is
deliberately small.
:::

## Cryptography and randomness

Hashes come from OpenSSL, the same library the TLS client uses. Each accepts
`bytes` or a string (whose UTF-8 bytes are hashed as they are):

| Call | Result |
| --- | --- |
| `sha256(data)` | The 32-byte SHA-256 digest as `bytes`. |
| `sha256_hex(data)` | The same digest as 64 lowercase hexadecimal characters. |
| `hmac_sha256(key, data)` | The 32-byte HMAC-SHA256 of `data` under `key`. |
| `rand_bytes(n)` | `n` bytes from the operating system's CSPRNG. |

```spark
print(sha256_hex("abc"));
// ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad

var mac = hmac_sha256("key", "message");
print(len(mac), type(mac));   // 32 bytes
print(len(rand_bytes(16)));   // 16
```

`rand()`, `randint()` and `srand()` are a fast, seedable, **non-cryptographic**
PRNG: never use them for tokens, keys or passwords. `rand_bytes` cannot be
seeded and never falls back to the predictable generator — if the CSPRNG fails
it raises `RuntimeError`. Error messages name the argument type but never echo
the key or the data.

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
spirit: they are the O(n) way to assemble a large text value. `bytes_builder()`
is the binary counterpart described above.

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

### Tokenizing a line

`examples/regex_tokenizer.spark`, run by the test suite, splits on whitespace,
recovers each field's character offset and classifies it with capture groups:

```spark
var source = "let total = 3 + 4 * count";

var fields = regex_split("\\s+", source);
var spans = regex_find_index("\\S+", source);

for (var i = 0; i < len(fields); i++) {
    var word = fields[i];
    var at = spans[i]["start"];
    var m = regex_match_groups(
        "^(?:(?P<number>\\d+)|(?P<name>[A-Za-z_]\\w*)|(?P<op>[-+*/=;]))$", word);

    if (m == nil) {
        print(format("%2d  error   %s", at, word));
    } else {
        var kind = "op";

        if (m["named"]["number"] != nil) {
            kind = "number";
        } else if (m["named"]["name"] != nil) {
            kind = "name";
        }
        print(format("%2d  %-7s %s", at, kind, word));
    }
}
```

```text
 0  name    let
 4  name    total
10  op      =
12  number  3
14  op      +
16  number  4
18  op      *
20  name    count
```

### Timing a block

```spark
fn timed(label, work) {
    var start = clock();
    var result = work();
    print(label, "took", clock() - start, "s");
    return result;
}
```

::: note
0.1.0 does not expose `rename` or `remove` for files, so a genuinely atomic
write needs `exec("mv ...")` with a validated path. The roadmap tracks a
richer file API.
:::

## Next

- [Networking](@networking/sockets) — sockets, TLS, HTTP and WebSockets.
- [Text](@stdlib/text) — string helpers, `format` and the builders.
- [Collections](@stdlib/collections) — JSON-friendly data structures.