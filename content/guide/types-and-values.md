Spark is dynamically typed: a variable holds a value, and the value knows its
type. `type(x)` reports it.

## The value types

| Type | Examples | `type()` | Truthiness |
| --- | --- | --- | --- |
| `nil` | `nil` | `"nil"` | falsey |
| `bool` | `true`, `false` | `"bool"` | by value |
| `int` | `42`, `-7`, `0xFF` | `"number"` | always truthy |
| `number` (float) | `3.14`, `1.5e3` | `"number"` | always truthy |
| `string` | `"hello"` | `"string"` | always truthy, including `""` |
| `bytes` | `bytes_from("hi")` | `"bytes"` | always truthy, including `bytes(0)` |
| `array` | `[1, 2]` | `"array"` | always truthy |
| `map` | `{"a": 1}` | `"map"` | always truthy |
| `function` | `fn(x) { ... }`, `print` | `"function"` | always truthy |
| `class` | `class Point { ... }` | `"class"` | always truthy |
| instance | `new Point(1, 2)` | the class name | always truthy |
| `string_builder` | `string_builder()` | `"string_builder"` | always truthy |
| `bytes_builder` | `bytes_builder()` | `"bytes_builder"` | always truthy |
| `file` | `open("data.txt")` | `"file"` | always truthy |
| `coroutine` | `spawn(worker)` | `"coroutine"` | always truthy |
| `channel` | `channel()` | `"channel"` | always truthy |
| `socket` | `tcp_connect(...)` | `"socket"` | always truthy |
| `server` | `tcp_listen(...)` | `"server"` | always truthy |
| `websocket` | `ws_connect(...)` | `"websocket"` | always truthy |

Only `nil` and `false` are falsey. `0`, `0.0`, `""`, `[]` and `{}` are all
truthy, which matters in conditions and in `and` / `or`.

```spark
if ([]) {
    print("an empty array is truthy");
}
print("" ? "truthy" : "falsey");   // truthy
```

## Integers and floats

There are two numeric types sharing the type name `"number"`:

- **int** — a signed 64-bit integer (`42`, `0xFF`, `1_000`).
- **float** — an IEEE 754 double (`3.14`, `1e3`, `42.0`).

A literal without a `.` or an exponent is an integer. Arithmetic between two
integers stays exact; mixing in a float promotes both to float. If an integer
result does not fit in 64 bits, it promotes to a float instead of overflowing:

```spark
print(1 + 2);                       // 3
print(10 / 4);                      // 2.5   — / is always float division
print(10 div 4);                    // 2     — div is truncating integer division
print(9223372036854775807);         // 9223372036854775807
print(9223372036854775807 + 1);     // 9.22337203685478e+18
```

`is_int(x)` distinguishes the two; `int(x)` and `float(x)` convert. `int` of a
float truncates toward zero.

```spark
print(type(1), type(1.0));    // number number
print(is_int(1), is_int(1.0));// true false
print(int(3.9), float(3));    // 3 3.0
```

The global constants `pi`, `nan` and `inf` are predefined. Following IEEE 754,
`nan == nan` is `false`; use `is_nan(x)` to test for it:

```spark
print(nan, is_nan(nan), nan == nan);       // nan true false
print(pi > 3.14, pi < 3.15, inf > 1e308);  // true true true
```

`inf` is positive infinity (`-inf` is its negation); `sqrt(-1)` and similar
domain errors raise `ValueError` rather than producing `nan`.

## Numeric literals

```spark
var decimal = 1_000_000;   // underscores may separate digits
var hex = 0xFF_FF;         // 65535
var binary = 0b1010;       // 10
var octal = 0o17;          // 15
var fraction = 1.25;
var exponent = 1.5e3;      // 1500.0
```

A separator must sit between two digits: `1__0` and `_10` are syntax errors.
An out-of-range integer literal becomes a float.

## Equality and identity

The rules differ by type:

```spark
print(1 == 1.0);                 // true
print("spark" == "spark");       // true — strings compare by content
var a = [1, 2];
var b = [1, 2];
print(a == b);                   // false — arrays compare by identity
print(a == a);                   // true

var m = {1: "one"};
print(m[1.0]);                   // one — 1 and 1.0 are the same key
```

- Numbers use numeric equality, so `1 == 1.0`.
- Strings and `bytes` compare by content.
- Arrays, maps, functions, instances and resource objects compare by identity.
- Map keys follow the same rules: content for strings and bytes, identity for
  objects, and canonical numeric equality (`map[1]` is `map[1.0]`).
- `nil == nil` is `true`; `nil` is never equal to another type. Comparison with
  `nil` always uses identity, even if a class overloads `__eq__`.

## Strings are immutable values

Strings are UTF-8 and immutable. Indexing returns a one-character string, and
positions count characters rather than bytes.

```spark
print(len("ñandú"));     // 5
print("spark"[0]);       // s
```

Because strings are immutable, `s += x` allocates a new string and copies the
accumulator. For large builds use `string_builder()`; see
[Strings](@guide/strings).

## Bytes are binary values

`bytes` is an immutable sequence of byte values, the binary counterpart of
`string`. It counts positions in bytes, not characters, and it accepts any value
from `0` to `255` — a string cannot hold a lone `0xFF` byte but a `bytes` value
can:

```spark
var abc = bytes_from([97, 98, 99]);      // b"abc"
var raw = bytes_from("héllo");           // b"h\xc3\xa9llo" — 6 bytes, 5 characters
print(len(abc), len(raw), type(abc));    // 3 6 bytes
print(abc[0], abc[-1]);                  // 97 99
print(abc + bytes_from("d"));            // b"abcd"
```

- `bytes(n)` builds `n` zero bytes; `bytes_from(array)` takes integers in
  `0..255`; `bytes_from(string)` copies the string's UTF-8 bytes unchanged.
- There is no `bytes` literal, so a byte value is always built at run time.
  `print` and `str` show a `b"..."` preview; `to_string(b)` is the lossless
  conversion back to text and raises `ValueError` on invalid UTF-8.
- There is no implicit conversion between `string` and `bytes`: `bytes_from`
  and `to_bytes` go one way, `to_string` goes the other, and mixing them in
  arithmetic (for example `bytes + string`) is a `TypeError`.
- Two `bytes` values compare by content, so they work as map keys; a string and
  the bytes with the same contents are different keys.

Binary I/O, the base64/hex codecs and compression are documented in
[Files, System and Data](@stdlib/files-and-system); `bytes_builder()` is the
mutable companion for assembling byte sequences.

## Arrays and maps are references

Arrays and maps are objects. Assigning one to another variable copies the
reference, not the contents:

```spark
var original = [1, 2, 3];
var alias = original;
push(alias, 4);
print(original);          // [1, 2, 3, 4]

var snapshot = copy(original);   // shallow copy
push(snapshot, 5);
print(original);          // [1, 2, 3, 4]
print(snapshot);          // [1, 2, 3, 4, 5]
```

`copy` is shallow: nested arrays and maps are still shared. The same holds for
instances and for functions (closures capture variables, not copies).

## Printing and conversion

`print` converts every argument with `str`, separated by spaces, and appends a
newline. `str(x)` uses `to_string()` on an instance when the class defines it.

```spark
class User {
    init(name) { self.name = name; }
    to_string() { return "User(${self.name})"; }
}

print(new User("Ada"));        // User(Ada)
print("hi ${new User("Ada")}");// hi User(Ada)
print([new User("Ada")]);      // [<User instance>]
```

::: note
Collections format their elements with the default representation. An
instance nested inside an array or map prints as `<ClassName instance>` even
when the class defines `to_string()`. This keeps formatting non-recursive and
avoids calling user code while another value is being built.
:::

`num(x)` parses a numeric string as a float; `int(x)` and `float(x)` also accept
numeric strings. `to_json` / `from_json` convert values to and from JSON; see
[Files, System and Data](@stdlib/files-and-system).

## What comes next

- [Operators](@guide/operators) — what you can do with these values.
- [Control Flow](@guide/control-flow) — how truthiness drives branches.
- [Arrays](@guide/arrays) and [Maps](@guide/maps) — the two collection types.
- [Strings](@guide/strings) — text in depth.