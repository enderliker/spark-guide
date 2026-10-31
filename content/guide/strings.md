Strings are UTF-8 text and immutable. Positions, indexes and lengths are counted
in **characters**, not bytes.

```spark
var greeting = "Hello, Spark!";
print(len(greeting));        // 13
print(len("ñandú"));         // 5 (5 characters, more bytes)
```

## Literals and escapes

```spark
var plain = "text";
var escapes = "line\n tab\t carriage\r quote\" backslash\\ nul\0";
var unicode = "á";      // á
var multiline = """
one
two
three
""";
```

The supported escapes are `\n`, `\t`, `\r`, `\\`, `\"`, `\0` and `\uXXXX`.
Any other escape is a syntax error.

## Interpolation

`${...}` embeds any expression, converted to text with the same rules as `str`:

```spark
var name = "Spark";
print("hello ${name}, 1 + 2 = ${1 + 2}");
// hello Spark, 1 + 2 = 3

print("cost: $$5");                    // cost: $5
print("${ "nested ${name}" }");        // nested Spark

var word = "abc";
print("upper: ${word.upper()}");       // upper: ABC
```

Use `$$` for a literal dollar sign. Interpolation builds the result with `+`
after converting each part, so interpolating a large number of values in a
loop still has the same cost as concatenation.

## Indexing

```spark
print("spark"[0]);       // s
print("spark"[-1]);      // k
print("spark"[1]);       // p
```

The index must be an integer. A negative index counts from the end; an
out-of-range index raises `IndexError`. Indexing yields a one-character string.

## Slicing

`text[start:end:step]` returns a new string; negative positions count from the
end and out-of-range positions are clamped.

```spark
print("spark"[1:3]);     // pa
print("spark"[:2]);      // sp
print("spark"[2:]);      // ark
print("spark"[::2]);     // srk
print("spark"[::-1]);    // kraps
print("spark"[10:20]);   // "" — clamped
```

## Concatenation

```spark
print("spark" + " " + "guide");   // spark guide
```

`+` only joins two strings. Adding a number is a `TypeError`; use
interpolation or `str`:

```spark
var n = 3;
print("n = " + str(n));
print("n = ${n}");
```

## Comparing

Strings compare by content with `==` and `!=`, and order with `<`, `<=`, `>`,
`>=`. Ordering is lexicographic by code point.

```spark
print("apple" < "banana");   // true
print("spark" == "spark");    // true
```

## The string helpers

| Call | Result |
| --- | --- |
| `len(s)` | Number of UTF-8 characters. |
| `substr(s, start, count?)` | Substring by characters; a negative start counts from the end. |
| `split(s, sep)` | Array of parts; an empty separator splits into characters. |
| `join(array, sep)` | Joins stringified elements. |
| `trim(s)` | Removes leading and trailing ASCII whitespace. |
| `upper(s)` / `lower(s)` | ASCII case conversion. |
| `repeat(s, n)` | `s` repeated `n` times. |
| `replace(s, old, new)` | Replaces every occurrence. |
| `starts_with(s, prefix)` / `ends_with(s, suffix)` | Prefix/suffix test. |
| `contains(s, sub)` | Substring test. |
| `index_of(s, sub)` | First character position or `-1`. |
| `chr(code)` / `ord(s)` | Unicode code point conversions. |
| `pad_start(s, width, fill?)` / `pad_end(...)` | Pad to a character width. |
| `slice(s, start, end?)` | Substring with clamping (no step). |

```spark
var s = "  Hello, World  ";
print(s.trim());                 // Hello, World
print(s.trim().upper());         // HELLO, WORLD
print("a,b,c".split(","));       // ["a", "b", "c"]
print(join(["a", "b"], "-"));    // a-b
print("spark".replace("a", "o"));// spork
print("7".pad_start(3, "0"));    // 007
print("ab".pad_end(4, "."));     // ab..
print("abcdef".slice(1, 4));     // bcd
print(substr("abcdef", -3));     // def
print(substr("abcdef", -2, 1));  // e
```

`upper` and `lower` only change ASCII letters, and `trim` only removes ASCII
whitespace; other characters are left untouched. `substr` requires a
non-negative `count`, and a `start` past the end returns `""`.

All of these also work as methods on the string: `s.trim()`, `s.split(",")`,
`s.upper()`. See [Text](@stdlib/text) for the full reference and edge cases.

## Building large strings

Strings are immutable, so `s += x` allocates a new string and copies the whole
accumulator on every step. Repeating it in a loop is **quadratic**.

```spark
// Don't do this for large inputs.
var s = "";
for (var i = 0; i < 100000; i += 1) {
    s += "x";
}
```

Use `string_builder()` instead, which appends into one growable buffer in
amortized O(1):

```spark
var builder = string_builder();
for (var i in range(3)) {
    builder.append("row ").append(i).append("; ");
}
print(builder.to_string());   // row 0; row 1; row 2;
print(builder.len());         // 21
```

`append` stringifies whatever it is given, so numbers, booleans and maps can
be appended directly. The function forms (`sb_append`, `sb_to_string`,
`sb_len`, `sb_clear`) are equivalent. Collecting fragments in an array and
using `join(parts, "")` is the other linear option.

```spark
var builder = string_builder("seed:");
builder.append(1).append(true);
print(builder.to_string());   // seed:1true
builder.clear();
```

Measured on the development machine, 200,000 single-character appends take
about 6 ms with the builder and about 2.2 s with `s += x`.

## Unicode notes

Because positions are characters, `len`, `substr`, indexing and slicing all
agree with each other. Byte-oriented operations are not exposed; `ord` and
`chr` convert between characters and code points.

```spark
print(ord("A"));          // 65
print(chr(0x1F600));      // 😀
print(len(chr(0x1F600))); // 1
```

Invalid UTF-8 cannot be represented in a Spark string. Binary data belongs on
the wire (sockets) or in files; the upcoming `bytes` type is tracked in the
[roadmap](@appendix/roadmap).

## Recipes

### Title case

```spark
fn title_case(text) {
    var parts = split(text, " ");
    for (var i = 0; i < len(parts); i += 1) {
        var word = parts[i];
        if (len(word) > 0) {
            parts[i] = upper(word[0]) + lower(word[1:]);
        }
    }
    return join(parts, " ");
}

print(title_case("hello spark guide"));   // Hello Spark Guide
```

### Truncating with an ellipsis

```spark
fn ellipsis(text, width) {
    if (len(text) <= width) {
        return text;
    }
    return text[:width - 1] + "…";
}

print(ellipsis("a long sentence", 8));   // a long …
```

### Checking for a prefix case-insensitively

```spark
fn starts_with_ci(text, prefix) {
    return starts_with(lower(text), lower(prefix));
}
```

## Next

- [Classes and Objects](@guide/classes-and-objects) — `to_string` and string interpolation.
- [Text](@stdlib/text) — every string native in one place.
- [Files, System and Data](@stdlib/files-and-system) — regular expressions and JSON.