This page is the reference for every operator in Spark, their precedence and
their exact semantics.

## Precedence table

From highest to lowest:

| Operators | Associativity | Description |
| --- | --- | --- |
| `()` `[]` `.` `?.` | left | call, indexing/slicing and member access |
| `++` `--` (postfix) | left | increment and decrement |
| `!` `not` `-` `~` `++` `--` (prefix) | right | logical, arithmetic and bitwise negation; increment and decrement |
| `**` | right | exponentiation |
| `*` `/` `%` `div` | left | multiplication, float division, remainder and integer division |
| `+` `-` | left | addition/concatenation and subtraction |
| `<<` `>>` | left | bit shifts |
| `<` `<=` `>` `>=` | left | ordering of two numbers or two strings |
| `in` `instanceof` | left | membership and type test |
| `==` `!=` | left | equality |
| `&` | left | bitwise AND |
| `^` | left | bitwise XOR |
| `\|` | left | bitwise OR |
| `and` | left | short-circuited conjunction |
| `or` | left | short-circuited disjunction |
| `??` | right | null-coalescing |
| `?:` | right | conditional expression |
| `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` `??=` | n/a | assignment statements |

::: warning Precedence surprises
Bitwise operators bind **looser** than comparisons and addition, so
`1 << 2 + 3` is `1 << 5` = `32`, and `2 + 3 & 1` is `(2 + 3) & 1` = `1`.
Use parentheses when mixing families.
:::

## Arithmetic

```spark
print(7 + 3, 7 - 3, 7 * 3);   // 10 4 21
print(7 / 2);                 // 3.5  — / is always float division
print(7 div 2, -7 div 2);     // 3 -3 — truncating integer division
print(7 % 2, -7 % 2);         // 1 -1 — remainder keeps the dividend's sign
print(2 ** 10);               // 1024
print(2 ** -1);               // 0.5
```

- `+` either adds two numbers, concatenates two strings or concatenates two
  `bytes`. It does **not** mix types: `"x" + 1`, `[1] + [2]` and
  `bytes_from("a") + "b"` are `TypeError`s. Use interpolation or `str(x)` to
  build text, and `bytes_from(x)` to build bytes.
- `div` requires two integers and truncates toward zero.
- Division or remainder by zero raises `ZeroDivisionError`.
- `**` is right-associative: `2 ** 3 ** 2` is `512`.
- Unary minus binds tighter than `**`, so `-2 ** 2` is `(-2) ** 2` = `4`.
  (Python would say `-4`.)
- A negative exponent produces a float.

## String concatenation and interpolation

```spark
print("spark" + " " + "guide");       // spark guide
print("value: ${1 + 2}");             // value: 3
print("literal dollar: $$5");         // literal dollar: $5
```

Interpolation accepts any expression and converts it with the same rules as
`str`. `$$` escapes a dollar sign. See [Strings](@guide/strings).

`bytes + bytes` is the binary counterpart: it appends one byte sequence to
another, and mixing a string in is a `TypeError`.

```spark
print(bytes_from("spark") + bytes_from("!"));   // b"spark!"
```

## Comparison

Numbers and strings can be ordered with `<`, `<=`, `>`, `>=`. Both operands
must be comparable with each other; comparing a number with a string is a
`TypeError`.

```spark
print(1 < 2, 2 <= 2, "apple" < "banana");   // true true true
print(1 == 1.0, "a" != "b");                // true true
```

`bytes` has **no ordering**: there is no `<` for two byte sequences, so sort
binary data with an explicit comparator. Equality is another matter — strings, numbers
and bytes compare by content, while objects compare by identity. See
[Types and Values](@guide/types-and-values).

```spark
print(bytes_from("spark") == bytes_from("spark"));   // true
print(bytes_from("spark") == "spark");               // false — different types
```

## Logic

`and` and `or` short-circuit and return one of their operands, not necessarily
a boolean:

```spark
print(nil or "default");   // default
print(0 or "default");     // 0        — 0 is truthy
print(1 and 2);            // 2
print(false and 1);        // false
print(not nil, not 0);     // true false
```

`!` is the symbolic spelling of `not`. Both treat only `nil` and `false` as
falsey.

## Null-coalescing

`??` returns its left operand unless it is `nil`, in which case it evaluates
and returns the right operand. Only `nil` triggers the fallback.

```spark
print(nil ?? "default");       // default
print(false ?? "fallback");    // false
print(0 ?? 10);                // 0
print(nil ?? nil ?? "third");  // third   (right-associative)
```

`??=` assigns only when the target is `nil`:

```spark
var cache = nil;
cache ??= {};
cache ??= {"ignored": true};
print(cache);                  // {}
```

## Conditional expression

`cond ? a : b` evaluates only the selected branch and is right-associative.

```spark
print(age >= 18 ? "adult" : "minor");
print(a ? b : c ? d : e);      // a ? b : (c ? d : e)
```

## Membership and type tests

`in` tests an array by value, a string by substring, a map by key and `bytes`
by byte value or byte subsequence. Any other container is a runtime error.

```spark
print("a" in ["a", "b"]);          // true
print("ar" in "spark");            // true
print("k" in {"k": 1});            // true
print(3 in [1, 2]);                // false
print(0x73 in bytes_from("spark"));               // true  — a byte value
print(bytes_from("par") in bytes_from("spark"));  // true  — a subsequence
```

The needle for `bytes` must be an integer in `0..255` or another `bytes`; a
string is a `TypeError`, since text and bytes never convert implicitly. Byte
offsets are counted in bytes, not characters.

`instanceof` tests whether the left operand is an instance of the class on the
right, subclasses included. `nil` and non-instances yield `false`, not an error.

```spark
print(new Dog("Rex") instanceof Animal);   // true for a subclass
print(nil instanceof Animal);              // false
```

Both bind looser than comparisons and tighter than equality:

```spark
print(2 in [1, 2] == true);   // true   ((2 in [1, 2]) == true)
print(1 < 2 in [true]);       // true   ((1 < 2) in [true])
```

## Bitwise operators

`&`, `|`, `^`, `~`, `<<` and `>>` require integers. `>>` is an arithmetic
( sign-preserving) shift. The shift count must be between `0` and `63`.

```spark
print(5 & 3, 5 | 3, 5 ^ 3, ~5);    // 1 7 6 -6
print(1 << 4, -16 >> 2);           // 16 -4
print(5 & 3 == 1);                 // true — & binds looser than ==
```

Compound forms exist: `x &= y`, `x |= y`, `x ^= y`, `x <<= y`, `x >>= y`.

## Increment and decrement

`++` and `--` are expressions. The postfix form yields the old value; the
prefix form yields the new one. They target variables and array or map
elements, not instance fields.

```spark
var i = 0;
print(i++, i, ++i);       // 0 1 2

var counts = {"a": 1};
counts["a"]++;
print(counts);            // {"a": 2}
```

## Optional chaining

`a?.b` and `a?.b(...)` behave like `a.b` but yield `nil` when `a` is `nil`.
Each link of a longer chain needs its own `?.`:

```spark
print(user?.name);            // nil when user is nil
print(user?.getName());       // the call form short-circuits too
print(user?.address?.city);   // nil when either link is nil
```

The same syntax works on any value with methods, including maps and strings:

```spark
print(counts?.len());
print(text?.upper());
```

## Indexing and slicing

`value[index]` reads one element. The index must be an integer; a negative
index counts from the end. Out-of-range indexing raises `IndexError`.

```spark
var a = [1, 2, 3, 4, 5];
print(a[0], a[-1]);       // 1 5
```

`value[start:end:step]` builds a new array, string or `bytes` from
`[start, end)` taken every `step` elements. Every part is optional, negative
positions count from the end, and out-of-range positions are **clamped** rather
than raising.

```spark
print(a[1:3]);            // [2, 3]
print(a[:2]);             // [1, 2]
print(a[2:]);             // [3, 4, 5]
print(a[::2]);            // [1, 3, 5]
print(a[::-1]);           // [5, 4, 3, 2, 1]
print(a[10:20]);          // []
print("spark"[1:3]);      // pa
print("spark"[::-1]);     // kraps
print(bytes_from("spark")[1:3]);   // b"pa"
```

`bytes` indexing yields an integer in `0..255` rather than a one-byte `bytes`
value, and a slice of `bytes` is a new `bytes`. Slicing counts bytes, not
characters:

```spark
var raw = bytes_from("ñandú");
print(len(raw), raw[0], raw[-1]);   // 7 195 186
print(raw[0:2]);                    // b"\xc3\xb1"
```

The rule to remember: **indexing is exact and raises; slicing clamps**. The
step must not be `0`. A slice is a value, not a place, so `a[1:3] = x` is a
syntax error. Only arrays, strings and bytes can be sliced.

## Assignment operators

`=`, `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=` and `??=`
are statements, not expressions. Their target must be a variable, an indexing
expression or an instance field. See
[Variables and Scope](@guide/variables-and-scope).

## Custom operators

Classes can define the meaning of arithmetic, comparison, indexing, `len` and
`to_string` through special methods (`__add__`, `__eq__`, `__index__`, ...).
See [Classes and Objects](@guide/classes-and-objects#operator-overloading).