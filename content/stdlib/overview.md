The standard library is a set of native functions registered in the VM. There
is no import statement for it: every native is available in every program.

```spark
print(type(42));           // number
print(len("spark"));       // 5
print(keys({"a": 1}));     // ["a"]
```

## Function form and method form

Most natives that take a value as their first argument also accept method
syntax on that value:

```spark
print(len("spark"));          // 5
print("spark".len());         // 5

print(upper("spark"));        // SPARK
print("spark".upper());       // SPARK

print(keys({"a": 1}));        // ["a"]
print({"a": 1}.keys());       // ["a"]
```

The method form is pure sugar: it passes the receiver as the first argument.
Use whichever reads better. One name differs:

| Function | Method |
| --- | --- |
| `del(map, key)` | `map.delete(key)` |

Method syntax is also how user methods on maps and classes are called, so the
same expression can dispatch to a user function. See
[Maps](@guide/maps#method-syntax-on-maps) and
[Classes and Objects](@guide/classes-and-objects).

## Categories

| Category | Page | Examples |
| --- | --- | --- |
| Values, types, conversion | this page | `type`, `str`, `int`, `assert`, `copy` |
| Text | [Text](@stdlib/text) | `substr`, `split`, `format`, `pad_start` |
| Collections | [Collections](@stdlib/collections) | `push`, `sort`, `map`, `reduce` |
| Numbers and math | [Numbers and Math](@stdlib/numbers-and-math) | `abs`, `sqrt`, `clamp`, `randint` |
| Files, system, binary data and codecs | [Files, System and Data](@stdlib/files-and-system) | `read_file`, `bytes_from`, `base64_encode`, `sha256`, `inflate`, `to_json` |
| Networking | [Networking](@networking/sockets) | `tcp_connect`, `http_get`, `ws_accept` |

## Values, types and conversion

| Call | Result |
| --- | --- |
| `print(a, b, ...)` | Prints the arguments separated by spaces and a newline. |
| `str(x)` | Text representation (uses `to_string()` on instances). |
| `num(x)` | Number from a numeric string, always a float; numbers pass through. |
| `int(x)` / `float(x)` | Convert between integer and float, or from a numeric string. |
| `is_int(x)` | Whether the value is an integer. |
| `is_nan(x)` | Whether the value is IEEE 754 NaN. |
| `type(x)` | Type name; a class name for instances. |
| `len(x)` | Length of a string (characters), bytes (bytes), array or map; `__len__` on instances. |
| `bytes(n)` / `bytes_from(x)` | New `bytes`: `n` zero bytes, or the bytes of an array of integers in `0..255` or of a string's UTF-8 encoding. |
| `to_string(b)` / `to_bytes(s)` | Convert between `bytes` and text; `to_string` rejects invalid UTF-8 with byte offset. |
| `bytes_to_array(b)` | Array with one integer in `0..255` per byte. |
| `assert(cond, message?)` | Stops the program when the condition is falsey. |
| `copy(value)` | Shallow copy of an array or map; other values are returned unchanged. |
| `isinstance(x, Class)` | Class or subclass test; a type-name string also works. |
| `is_a(x, Class)` | Like `isinstance`, but the second argument must be a class. |
| `gc()` | Runs a garbage-collection cycle immediately. |

```spark
print(str(42), num("3.5"), int(3.9), float(3));    // 42 3.5 3 3.0
print(type("x"), type([]), type({}), type(print)); // string array map function
print(len("ñandú"), len([1, 2]), len({"a": 1}));   // 5 2 1

var a = [1, 2];
var b = copy(a);
push(b, 3);
print(a, b);                                        // [1, 2] [1, 2, 3]

var raw = bytes_from("hi");
print(type(raw), len(raw), to_string(raw));         // bytes 2 hi
print(bytes_to_array(bytes_from([0xff, 0x00])));    // [255, 0]
```

::: note `type()` for numbers
Both integers and floats report `"number"`. Use `is_int(x)` to tell them apart.
:::

The other type names are `"nil"`, `"bool"`, `"bytes"`, `"class"`, `"file"`,
`"string_builder"`, `"bytes_builder"`, `"coroutine"`, `"channel"`, `"socket"`,
`"server"` and `"websocket"`.

## Callbacks

The higher-order natives — `map`, `filter`, `reduce`, `each`, `any`, `all` and
`sort` (or its alias `sort_by`) — accept either a closure or another native:

```spark
print(map([1, 2, 3], fn(x) => x * 2));   // [2, 4, 6]
print(map([1, 2, 3], str));              // ["1", "2", "3"]
```

Callbacks run at a deeper `run_depth`. They cannot `yield`, block on a channel
or perform a would-block socket call; those operations raise `RuntimeError`
inside a callback. See
[Functions and Closures](@guide/functions-and-closures#higher-order-functions).

## Argument checking

Natives validate their arguments and raise categorized errors:

- `TypeError` when an argument has the wrong type.
- `ValueError` when a value is outside the accepted domain (negative sizes, bad
  conversion, zero slice step).
- `ArityError` when the number of arguments is wrong.
- `IndexError` for out-of-range indexes.

```spark
// int("abc")        -> ValueError
// sqrt(-1)          -> ValueError
// push("no", 1)     -> TypeError
// pop([])           -> IndexError
// slice(1, 2, 3)    -> TypeError
```

The exact behavior of each function is documented on its category page.

## Globals

| Name | Meaning |
| --- | --- |
| `pi` | The constant π. |
| `nan` | IEEE 754 NaN. |
| `inf` | Positive infinity. |
| `argv` | Script path and arguments; empty in the REPL. |
| `_` | REPL only: result of the last expression statement. |

## Optional arguments

Several natives have optional trailing arguments (`substr(text, start,
count?)`, `get(map, key, default?)`, `range(start, end, step?)`,
`round(x, digits?)`, `split(text, sep, limit?)`, `trim(text, chars?)`,
`sort(array, comparator?)`), and a few are variadic (`print`, `min`, `max`,
`format`, `spawn`). Optional arguments may be omitted or passed as `nil` where
the documentation says so; a missing default is not always the same as an
explicit `nil` (for example, `http_get` treats `nil` as "use the default").

## Next

- [Text](@stdlib/text) — strings in depth.
- [Collections](@stdlib/collections) — arrays, maps and callbacks.
- [Numbers and Math](@stdlib/numbers-and-math) — the numeric surface.
- [Files, System and Data](@stdlib/files-and-system) — I/O, JSON and regex.