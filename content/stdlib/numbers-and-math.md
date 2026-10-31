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
| `round(x)` | Nearest integer, halfway cases away from zero. |
| `abs(x)` | Absolute value. |

An integer input is returned unchanged. The result of `floor`, `ceil` and
`round` is an integer.

```spark
print(floor(2.9), ceil(2.1), round(2.5));   // 2 3 3
print(round(-2.5));                          // -3
print(abs(-7), abs(-7.5));                   // 7 7.5
print(floor(5));                             // 5
```

## Powers and roots

| Call | Result |
| --- | --- |
| `sqrt(x)` | Square root; `ValueError` on a negative input. |
| `pow(x, y)` | `x` raised to `y`; equivalent to `x ** y`. |

```spark
print(sqrt(81));        // 9
print(pow(2, 10));      // 1024
print(2 ** 10);         // 1024
print(2 ** -1);         // 0.5
print((-2) ** 2);       // 4
print(-2 ** 2);         // 4 — unary minus binds tighter than **
```

::: warning `sqrt(-1)` is an error
`sqrt` raises `ValueError` instead of returning NaN. Use `is_nan` to test
values that come from other computations, and check the sign before calling
`sqrt`.
:::

## Trigonometry and logarithms

| Call | Result |
| --- | --- |
| `sin(x)` / `cos(x)` | Sine and cosine in radians. |
| `log(x)` | Natural logarithm. |
| `exp(x)` | e raised to `x`. |

```spark
print(sin(0), cos(0));          // 0 1
print(log(exp(1)));             // 1
print(exp(0));                  // 1
```

Only the functions listed here are provided. There is no `tan`, `atan2`,
`log10` or hyperbolic family in 0.1.0; the [roadmap](@appendix/roadmap) tracks
a larger math surface.

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

There is no `printf`-style precision control in the standard library. For
fixed decimals, round and format manually:

```spark
fn fixed(value, digits) {
    var scale = pow(10, digits);
    return str(round(value * scale) / scale);
}

print(fixed(3.14159, 2));   // 3.14
```

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

## Next

- [Files, System and Data](@stdlib/files-and-system) — time, sleep and I/O.
- [Operators](@guide/operators) — the full expression reference.
- [Types and Values](@guide/types-and-values) — the numeric model.