Spark strings are UTF-8 and immutable. Every helper on this page counts
positions in **characters**, not bytes, and all of them have a method form on
the string.

## Reference

| Call | Result |
| --- | --- |
| `len(s)` | Number of UTF-8 characters. |
| `substr(s, start, count?)` | Substring starting at `start`; a negative `start` counts from the end. |
| `split(s, sep)` | Array of parts; an empty separator splits into characters. |
| `join(array, sep)` | Text joining the stringified elements. |
| `trim(s)` | Leading and trailing ASCII whitespace removed. |
| `upper(s)` / `lower(s)` | ASCII upper/lower case. |
| `repeat(s, n)` | `s` repeated `n` times. |
| `replace(s, old, new)` | Every occurrence of `old` replaced with `new`. |
| `starts_with(s, prefix)` | Prefix test. |
| `ends_with(s, suffix)` | Suffix test. |
| `contains(s, sub)` | Substring test. |
| `index_of(s, sub)` | First character position, or `-1`. |
| `chr(code)` | One-character string for a Unicode code point. |
| `ord(s)` | Unicode code point of the first character; `s` must be non-empty. |
| `pad_start(s, width, fill?)` | Pads on the left to `width` characters. |
| `pad_end(s, width, fill?)` | Pads on the right to `width` characters. |
| `slice(s, start, end?)` | New string for `[start, end)` with clamping; no step. |

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
print(join(["a", "b", "c"], "-")); // a-b-c
print(join([1, 2, 3], ", "));      // 1, 2, 3
print("a,b,c".split(",").join("|")); // a|b|c
```

`join` stringifies every element, so numbers and other values work without a
separate `map(..., str)`.

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

## Replacing and repeating

```spark
print(replace("banana", "a", "o"));   // bonono
print(repeat("ab", 3));               // ababab
print(repeat("x", 0));                // ""
```

`replace` replaces every occurrence and does not interpret the replacement
specially (`$1` is literal text).

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

There is no regular-expression split native, but `regex_find` can do it:

```spark
var words = regex_find("\\s+", "  one   two  three ");
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