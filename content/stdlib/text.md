Spark strings are UTF-8 and immutable. Every helper on this page counts
positions in **characters**, not bytes, and all of them have a method form on
the string.

## Reference

| Call | Result |
| --- | --- |
| `len(s)` | Number of UTF-8 characters. |
| `substr(s, start, count?)` | Substring starting at `start`; a negative `start` counts from the end. |
| `split(s, sep, limit?)` | Array of parts; an empty separator splits into characters; `limit` caps the field count. |
| `join(array, sep)` | Text joining the stringified elements. |
| `format(template, args...)` | printf-style text from a template and positional arguments (see below). |
| `trim(s, chars?)` | Leading and trailing ASCII whitespace, or any of the whole characters in `chars`. |
| `upper(s)` / `lower(s)` | ASCII upper/lower case. |
| `repeat(s, n)` | `s` repeated `n` times. |
| `replace(s, old, new)` | Every occurrence of `old` replaced with `new`. |
| `starts_with(s, prefix)` | Prefix test. |
| `ends_with(s, suffix)` | Suffix test. |
| `contains(s, sub)` | Substring test. |
| `index_of(s, sub)` | First character position, or `-1`. |
| `count(s, sub)` | Non-overlapping occurrences of `sub`; an empty `sub` is `len(s) + 1`. |
| `chr(code)` | One-character string for a Unicode code point. |
| `ord(s)` | Unicode code point of the first character; `s` must be non-empty. |
| `pad_start(s, width, fill?)` | Pads on the left to `width` characters. |
| `pad_end(s, width, fill?)` | Pads on the right to `width` characters. |
| `slice(s, start, end?)` | New string for `[start, end)` with clamping; no step. |
| `to_bytes(s)` | The string's UTF-8 bytes as a `bytes` value. |

The `a[start:end:step]` syntax is the only way to slice with a step. See
[Strings](@guide/strings).

## Length and substrings

```spark
print(len("spark"));              // 5
print(len("ñandú"));              // 5 characters
print(substr("abcdef", 1, 3));    // bcd
print(substr("program", 5));      // am
print(substr("abcdef", -3));      // def
print(substr("abcdef", -2, 1));   // e
print(substr("abc", 99));         // "" — start past the end
print("abcdef".slice(1, 4));      // bcd
```

- `substr` takes `count` characters, or the rest when omitted.
- A negative `start` counts from the end.
- `count` must not be negative (`ValueError`).
- A `start` beyond the end returns `""`.

`slice(s, start, end?)` is the native equivalent of `s[start:end]`: negative
positions count from the end and out-of-range positions are clamped.

## Splitting and joining

```spark
print(split("a,b,c", ","));        // ["a", "b", "c"]
print(split("spark", ""));         // ["s", "p", "a", "r", "k"]
print(split("a,b,c", ",", 2));     // ["a", "b,c"]
print(join(["a", "b", "c"], "-")); // a-b-c
print(join([1, 2, 3], ", "));      // 1, 2, 3
print("a,b,c".split(",").join("|")); // a|b|c
```

`join` stringifies every element, so numbers and other values work without a
separate `map(..., str)`.

The optional `limit` caps the number of fields, exactly as `regex_split` does:
it is the maximum field count, `0` returns `[]`, a negative value (or no
argument) means no limit, and the last field keeps the unresolved remainder.
The separator stays a literal string, and an empty separator splits into
characters. See
[Files, System and Data](@stdlib/files-and-system#regular-expressions).

```spark
print(split("a,b,c", ",", 0));     // []
print(split("a,b,c", ",", 1));     // ["a,b,c"]
print(split("spark", "", 3));      // ["s", "p", "ark"]
```

::: tip Splitting a line
`socket.recv_line()` strips the newline for you. For text files, `read_line`
also returns the line without its terminator; `split(line, "\n")` is only
needed when you read a whole file at once.
:::

## Trimming and case

```spark
print(trim("  hello  "));       // hello
print(upper("hello"));          // HELLO
print(lower("HELLO"));          // hello
print("  MiXeD  ".trim().lower());   // mixed
```

`trim`, `upper` and `lower` are ASCII-only. Non-ASCII characters are left
untouched:

```spark
print(upper("ñandú"));          // ñANDÚ
```

Case conversion for full Unicode is not part of 0.1.0; see the
[roadmap](@appendix/roadmap).

With a second argument, `trim` strips a **set of characters** instead of
whitespace. Each character is removed whole — the set is not a prefix — so
`trim("ñandú", "ñú")` is `"and"`, and only the ends are touched:

```spark
print(trim("xxhixx", "x"));     // hi
print(trim("--spark--", "-"));  // spark
print(trim("ñandú", "ñú"));     // and
print(trim("spark", ""));       // spark — an empty set removes nothing
```

## Searching

```spark
var text = "the spark guide";

print(contains(text, "spark"));    // true
print(index_of(text, "guide"));    // 10
print(index_of(text, "missing"));  // -1
print(starts_with(text, "the"));   // true
print(ends_with(text, "guide"));   // true
```

`contains` and `index_of` also work on arrays (by value) and maps (by key):

```spark
print(contains([1, 2, 3], 2));     // true
print(index_of([1, 2, 3], 3));     // 2
```

`count(s, sub)` counts **non-overlapping** occurrences, so `count("aaaa", "aa")`
is `2` rather than `3`. An empty `sub` counts `len(s) + 1` — the number of
positions where it occurs:

```spark
print(count("banana", "a"));     // 3
print(count("aaaa", "aa"));      // 2
print(count("abc", ""));         // 4
print(count("", "a"));           // 0
```

## Replacing and repeating

```spark
print(replace("banana", "a", "o"));   // bonono
print(repeat("ab", 3));               // ababab
print(repeat("x", 0));                // ""
```

`replace` replaces every occurrence and does not interpret the replacement
specially (`$1` is literal text).

## Formatting

`format(template, args...)` builds text from a template and positional
arguments in one pass, so it is linear in the output size. `%` keeps its meaning
as the modulo operator; there is no formatting operator, only this native.

```spark
print(format("%s scored %d (%08.3f%%)", "Ada", 42, 98.5));
// Ada scored 42 (0098.500%)
print(format("%x %X %o %b", 255, 255, 8, 5));   // ff FF 10 101
print(format("%c%c", 65, 233));                 // Aé
print(format("%-6s|%+d|%%", "hi", 7));          // hi    |+7|%
```

| Specifier | Argument | Result |
| --- | --- | --- |
| `%s` | any value | `str(value)`, so an instance's `to_string()` is honored. |
| `%d` / `%i` | integer, or a float with no fractional part | Decimal digits. |
| `%x` / `%X` | integer | Hexadecimal, lowercase / uppercase. |
| `%o` | integer | Octal. |
| `%b` | integer | Binary. |
| `%f` | number | Fixed notation, six decimals by default. |
| `%g` | number | Shortest of fixed/exponential, six significant digits by default. |
| `%c` | integer | One UTF-8 character for a code point in `0..0x10FFFF`. |
| `%%` | none | A literal `%`. |

- `-` left-justifies, `0` zero-pads a number after its sign, and `+` forces a
  sign on `%d` / `%i` / `%f` / `%g`.
- Width is the minimum field size in characters; `.precision` is the decimals
  for `%f`, the significant digits for `%g`, the minimum digits for the integer
  bases, and a maximum character count for `%s` (a UTF-8 sequence is never split).
- `%d` on a float truncates **only** when it has no fractional part, so `3.0`
  prints `3` while `3.5` is a `TypeError` — no value is rounded silently.
- An argument that does not match its specifier is a `TypeError`. A missing
  argument (or one left over beyond the template) is an `ArityError`, and an
  unknown specifier, a trailing `%` or an out-of-range width is a `ValueError`.

`format` is the right tool when the layout matters: columns, numeric bases and
fixed decimals are awkward to express with interpolation alone.

```spark
for (var row in [["Ada", 3], ["Grace", 12]]) {
    print(format("%-8s %3d", row[0], row[1]));
}
// Ada        3
// Grace     12
```

## Padding

```spark
print(pad_start("7", 3, "0"));    // 007
print(pad_end("7", 3, "0"));      // 700
print(pad_start("1", 4));         //    1
print(pad_end("1", 4, "."));      // 1...
```

The width is measured in characters. If the text is already at least `width`
characters long, it is returned unchanged.

## Code points

```spark
print(ord("A"));          // 65
print(ord("ñ"));          // 241
print(chr(65));           // A
print(chr(0x1F600));      // 😀
print(len(chr(0x1F600))); // 1
```

`ord` requires a non-empty string; an empty one is a `ValueError`.

## Text and bytes

`to_bytes(text)` (also `text.to_bytes()`) is the exact UTF-8 encoding of a
string, and `to_string(bytes)` is the way back. Neither ever converts
implicitly, and `to_string` raises `ValueError` naming the byte offset when the
payload is not valid UTF-8:

```spark
var raw = to_bytes("héllo");
print(len("héllo"), len(raw));       // 5 6 — characters against bytes
print(to_string(raw) == "héllo");    // true
print(bytes_to_array("A".to_bytes()));  // [65]
```

The binary side — codecs, `bytes_builder`, files and sockets — lives in
[Files, System and Data](@stdlib/files-and-system).

## Interpolation

Interpolation is syntax rather than a native, but it is the usual way to build
text:

```spark
var name = "Ada";
var age = 36;
print("${name} is ${age}");
print("next year: ${age + 1}");
print("literal: $$5");
```

Every expression is converted with `str`, so instances use `to_string()`.
Nested interpolation works: `"${ "inner ${name}" }"`.

## Building large strings

Use `string_builder()` for repeated appends:

| Call | Result |
| --- | --- |
| `string_builder(initial?)` | New builder; a string seeds content, an integer sets capacity. |
| `sb_append(sb, value)` | Appends the stringified value; returns the builder. |
| `sb_to_string(sb)` | The accumulated text as an immutable string. |
| `sb_len(sb)` | Length in UTF-8 characters. |
| `sb_clear(sb)` | Empties the builder; returns it. |

Method forms: `sb.append(value)`, `sb.to_string()`, `sb.len()`, `sb.clear()`.

```spark
var sb = string_builder();
sb.append("id=").append(42).append(";");
print(sb.to_string());   // id=42;
print(sb.len());         // 6
sb.clear();
print(sb.len());         // 0
```

Appending 200,000 single characters takes about 6 ms with the builder and about
2.2 s with `s += "x"` on the development machine. The difference is
algorithmic: `+=` is O(n²) because strings are immutable.

## Recipes

### Reversing a string

```spark
fn reverse_text(text) {
    return text[::-1];
}

print(reverse_text("spark"));   // kraps
```

### Checking a palindrome

```spark
fn is_palindrome(text) {
    var normalized = lower(replace(text, " ", ""));
    return normalized == normalized[::-1];
}

print(is_palindrome("Never odd or even"));   // true
```

### Splitting on runs of whitespace

`split` takes a literal separator. When the separator is a pattern, use
`regex_split` and drop the empty fields at either end:

```spark
var words = [];
for (var word in regex_split("\\s+", "  one   two  three ")) {
    if (len(word) > 0) {
        push(words, word);
    }
}
print(words);   // ["one", "two", "three"]
```

See [Files, System and Data](@stdlib/files-and-system#regular-expressions).

### Wrapping text

```spark
fn wrap(text, width) {
    var words = split(text, " ");
    var lines = [];
    var line = "";

    for (var word in words) {
        if (len(line) > 0 and len(line) + 1 + len(word) > width) {
            push(lines, line);
            line = word;
        } else if (len(line) == 0) {
            line = word;
        } else {
            line += " " + word;
        }
    }
    if (len(line) > 0) {
        push(lines, line);
    }
    return join(lines, "\n");
}

print(wrap("the quick brown fox jumps", 12));
```

## Next

- [Collections](@stdlib/collections) — arrays and maps.
- [Files, System and Data](@stdlib/files-and-system) — reading and writing text.
- [Strings](@guide/strings) — the language-level view.