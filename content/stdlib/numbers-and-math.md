Spark has 64-bit integers and IEEE 754 doubles. Both report `type(x)` as
`"number"`; `is_int(x)` distinguishes them.

## Conversion and inspection

| Call | Result |
| --- | --- |
| `num(x)` | Float from a numeric string; numbers pass through. |
| `int(x)` | Integer from a number or numeric string; floats truncate toward zero. |
| `float(x)` | Float from an integer or numeric string. |
| `is_int(x)` | `true` when the value is an integer. |
| `is_nan(x)` | `true` when the value is IEEE 754 NaN. |
| `abs(x)` | Absolute value; an integer stays an integer. |
| `min(a, b, ...)` / `max(a, b, ...)` | Smallest/largest argument, or over one array argument. |
| `sum(array)` | Sum of numeric elements; an integer when all are integers. |

```spark
print(num("3.5"));          // 3.5
print(num("42"));           // 42.0
print(int(3.9), int(-3.9)); // 3 -3
print(float(3));            // 3.0

print(is_int(42), is_int(42.0));   // true false
print(type(42), type(42.0));       // number number
```

`int("abc")` raises `ValueError`. `num` and `float` accept decimals and
exponents, not hex literals.

## Rounding

| Call | Result |
| --- | --- |
| `floor(x)` | Largest integer not greater than `x`. |
| `ceil(x)` | Smallest integer not less than `x`. |
| `trunc(x)` | Nearest integer toward zero. |
| `round(x, digits?)` | Nearest integer, halfway cases away from zero; with `digits`, that many decimal places. |
| `abs(x)` | Absolute value. |

An integer input is returned unchanged. The result of `floor`, `ceil`, `trunc`
and `round` without `digits` is an integer.

```spark
print(floor(2.9), ceil(2.1), round(2.5));   // 2 3 3
print(trunc(2.7), trunc(-2.7));              // 2 -2
print(round(-2.5));                          // -3
print(abs(-7), abs(-7.5));                   // 7 7.5
print(floor(5));                             // 5
```

`round(x, digits)` scales by a power of ten and rounds back, and `digits` must
be between `0` and `15`:

```spark
print(round(3.14159, 2));   // 3.14
print(round(2.5, 1));       // 2.5
print(round(-2.55, 1));     // -2.6
```

Because the scaling happens in binary floating point, a decimal that has no
exact binary form can surprise you: `round(1.005, 2)` is `1`, and
`round(2.675, 2)` is `2.68`. For display, prefer `format("%.2f", x)`, which
formats without changing the value.

## Powers and roots

| Call | Result |
| --- | --- |
| `sqrt(x)` | Square root; `ValueError` on a negative input. |
| `cbrt(x)` | Cube root; a negative input is allowed. |
| `pow(x, y)` | `x` raised to `y`; equivalent to `x ** y`. |
| `hypot(x, y)` | `sqrt(x*x + y*y)` without intermediate overflow. |

```spark
print(sqrt(81));        // 9
print(pow(2, 10));      // 1024
print(2 ** 10);         // 1024
print(2 ** -1);         // 0.5
print((-2) ** 2);       // 4
print(-2 ** 2);         // 4 — unary minus binds tighter than **
print(cbrt(-27), cbrt(8));    // -3 2
print(hypot(3, 4));           // 5
```

::: warning `sqrt(-1)` is an error
`sqrt` raises `ValueError` instead of returning NaN. Use `is_nan` to test
values that come from other computations, and check the sign before calling
`sqrt`. `cbrt` is the exception: it accepts negative inputs.
:::

## Trigonometry and logarithms

| Call | Result |
| --- | --- |
| `sin(x)` / `cos(x)` / `tan(x)` | Trigonometric functions in radians. |
| `asin(x)` / `acos(x)` | Inverse functions; input outside `[-1, 1]` is a `ValueError`. |
| `atan(x)` / `atan2(y, x)` | Inverse tangent of one value, or of `y/x` with the correct quadrant. |
| `log(x)` / `log2(x)` / `log10(x)` | Natural, base-2 and base-10 logarithms; a non-positive argument is a `ValueError`. |
| `exp(x)` | e raised to `x`. |

All of them return a float, even for integral results.

```spark
print(sin(0), cos(0), tan(0));          // 0 1 0
print(asin(1), acos(0));                // 1.5707963267949 1.5707963267949
print(atan(1), atan2(1, 1));            // 0.785398163397448 0.785398163397448
print(log(exp(1)));                     // 1
print(log2(8), log10(1000));            // 3 3
print(exp(0));                          // 1
```

`atan2(y, x)` is the one to reach for when the signs of both coordinates
matter: for the point with `x = -1` and `y = 1`, `atan2(1, -1)` is `3π/4`,
while `atan(1 / -1)` is only `-π/4` — the single-argument form cannot tell
which quadrant the point is in.

## Integer helpers

| Call | Result |
| --- | --- |
| `sign(x)` | `-1`, `0` or `1` as an integer; `nan` is a `ValueError`. |
| `clamp(x, low, high)` | `x` limited to `[low, high]`; returns whichever of the three values wins. |
| `gcd(a, b)` / `lcm(a, b)` | Greatest common divisor and least common multiple of two integers. |

```spark
print(sign(-3), sign(0), sign(2.5));         // -1 0 1
print(clamp(15, 0, 10), clamp(-5, 0, 10));   // 10 0
print(gcd(12, 18), gcd(-12, 18), lcm(4, 6)); // 6 6 12
```

`gcd` and `lcm` use the magnitudes, so the result is never negative. A
non-integer argument, `low > high`, or an `lcm` result outside the 64-bit range
is a `ValueError`; `clamp` returns the winning argument unchanged, integer or
float.

## Minimum, maximum and sum

```spark
print(min(3, 1, 4), max(3, 1, 4));    // 1 4
print(min([3, 1, 4]), max([3, 1, 4]));// 1 4
print(sum([1, 2, 3]));                 // 6
print(sum([1, 2.5]));                  // 3.5
print(sum([]));                        // 0
```

`min` and `max` take either several arguments or a single array. `sum`
requires numeric elements.

## Integer versus float semantics

- Arithmetic between two integers stays an integer when the result fits in 64
  bits.
- Mixing an integer and a float promotes both to float.
- An integer result that would overflow 64 bits promotes to a float instead of
  wrapping.
- `/` is always float division. `div` is truncating integer division and
  requires two integers. `%` is the remainder and keeps the dividend's sign.

```spark
print(7 / 2);              // 3.5
print(7 div 2);            // 3
print(-7 div 2);           // -3
print(-7 % 2);             // -1
print(9223372036854775807 + 1);   // 9.22337203685478e+18
```

Bitwise operators require integers:

```spark
print(5 & 3, 5 | 3, 5 ^ 3, ~5);   // 1 7 6 -6
print(1 << 4, -16 >> 2);          // 16 -4
```

See [Operators](@guide/operators#bitwise-operators).

## Output formatting

`print` and `str` format floats with up to 15 significant digits:

```spark
print(1 / 3);          // 0.333333333333333
print(1e20);           // 1e+20
print(0.1 + 0.2);      // 0.3
print(0.1 + 0.2 == 0.3); // false — the formatting hides the difference
print(3.0);            // 3
print(-0.0);           // -0
```

::: warning Printing can hide precision
`0.1 + 0.2` prints as `0.3` but is not equal to `0.3`, because display uses 15
significant digits. Do not use printed output to verify float equality; use
an explicit tolerance.
:::

For fixed decimals or aligned columns, use `format`. It lays out the text
without changing the value, which is what you want at the edge of a program:

```spark
print(format("%.2f", 3.14159));     // 3.14
print(format("%8.3f", -3.14159));   //   -3.142
print(format("%08.3f", -3.14159));  // -003.142
print(format("%g", 0.0000123));     // 1.23e-05
```

See [Text](@stdlib/text#formatting) for the full specifier table.

::: warning Floating-point money
Do not store money in floats. Use integer cents (`1999`) and format at the
edge. `0.1 + 0.2 != 0.3` is not a Spark bug; it is IEEE 754.
:::

## NaN

`nan` is a predefined global constant:

```spark
print(nan);            // nan
print(is_nan(nan));    // true
print(nan == nan);     // false
print(nan != nan);     // true
```

Any comparison involving NaN is false, except `!=`, which is true. Use
`is_nan(x)` rather than `x == nan`.

## Random numbers

| Call | Result |
| --- | --- |
| `rand()` | Float in `[0.0, 1.0)`. |
| `randint(max)` | Inclusive integer in `[0, max]`. |
| `randint(min, max)` | Inclusive integer in `[min, max]`. |
| `srand(seed)` | Seeds the PRNG with an integer or float. |

```spark
srand(42);
print(rand());                     // 0.741564878771823
var dice = randint(1, 6);
print(dice >= 1 and dice <= 6);   // true
```

`randint` validates its range and raises `ValueError` when `min > max`.

## Constants

| Name | Value |
| --- | --- |
| `pi` | π |
| `nan` | IEEE 754 NaN |
| `inf` | Positive infinity; `-inf` is its negation. |

`inf` is an ordinary float — `is_nan(inf)` is `false`, `inf > 1e308` is `true`,
and `inf - inf` is NaN. Domain errors still raise rather than returning it.

## Next

- [Files, System and Data](@stdlib/files-and-system) — time, sleep and I/O.
- [Operators](@guide/operators) — the full expression reference.
- [Types and Values](@guide/types-and-values) — the numeric model.