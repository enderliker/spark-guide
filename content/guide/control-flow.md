Any value can be a condition. `nil` and `false` are falsey; everything else,
including `0`, `0.0`, `""`, `[]` and `{}`, is truthy. See
[Types and Values](@guide/types-and-values) if that surprises you.

## if / else

```spark
if (temperature > 30) {
    print("hot");
} else if (temperature > 15) {
    print("mild");
} else {
    print("cold");
}
```

Braces are required. There is no `elif`; use `else if`. The conditional
expression `cond ? a : b` is the expression form (see
[Operators](@guide/operators#conditional-expression)).

## while

```spark
var n = 3;
while (n > 0) {
    print(n);
    n -= 1;
}
```

## do / while

The body runs at least once:

```spark
var attempt = 0;
do {
    attempt += 1;
} while (attempt < 3);

print(attempt);   // 3
```

## C-style for

```spark
for (var i = 0; i < 10; i += 1) {
    if (i == 3) {
        continue;
    }
    if (i == 8) {
        break;
    }
    print(i);
}
```

All three parts are optional:

```spark
for (;;) {
    break;
}
```

A variable declared in the init clause (`var i`) is scoped to the loop. The
loop variable itself is a single variable shared by every iteration — a detail
that matters for closures; see
[Functions and Closures](@guide/functions-and-closures#closing-over-the-loop-variable).

## for-in

`for-in` iterates over the elements of an array, the keys of a map or the
characters of a string:

```spark
for (var value in [10, 20, 30]) {
    print(value);
}

for (var key in {"a": 1, "b": 2}) {
    print(key);
}

for (var character in "spark") {
    print(character);
}
```

Arrays can yield the index and the value together:

```spark
for (var index, value in ["a", "b", "c"]) {
    print(index, value);
}
```

```text
0 a
1 b
2 c
```

The loop variable in a `for-in` is also shared across iterations. A variable
declared *inside* the body is fresh each time.

## switch

```spark
switch (status) {
    case 200:
        print("OK");
    case 404:
        print("Not Found");
    default:
        print("something else");
}
```

- The subject is evaluated once and compared with each `case` value using
  `==`.
- Case values are expressions, evaluated in order until one matches.
- **Cases do not fall through.** Only the matching body runs, and it ends
  automatically. An empty case body does nothing.
- `default` may appear anywhere and runs only when no case matches.
- `break` exits the switch; `continue` targets the enclosing loop.

Because case bodies are expressions, common status handling reads nicely:

```spark
fn reason(status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "Created";
        case 404: return "Not Found";
        default: return "Unknown";
    }
}
```

## Labelled loops

`while`, `do/while`, `for` and `for-in` accept a label. `break label` and
`continue label` target that loop instead of the innermost one:

```spark
outer: for (var i = 0; i < 3; i += 1) {
    for (var j = 0; j < 3; j += 1) {
        if (j == 1) {
            continue outer;
        }
        if (i == 2) {
            break outer;
        }
    }
}
```

```text
0 0
1 0
2 0
```

The label must be followed by a loop, and the loop it names must enclose the
`break` or `continue`; otherwise it is a compile error.

## break and continue

| Statement | Allowed in |
| --- | --- |
| `break;` | a loop or a `switch` |
| `continue;` | a loop |
| `return;` | a function |
| `break label;` / `continue label;` | inside the named enclosing loop |

## A worked example: FizzBuzz

```spark
for (var i = 1; i <= 20; i += 1) {
    if (i % 15 == 0) {
        print("FizzBuzz");
    } else if (i % 3 == 0) {
        print("Fizz");
    } else if (i % 5 == 0) {
        print("Buzz");
    } else {
        print(i);
    }
}
```

## Iterating deterministically

Maps in Spark preserve no specified iteration order across runs in principle,
though the implementation uses an open-addressing table and typically yields a
stable order for a given insertion sequence. Do not depend on it: sort the keys
when output order matters.

```spark
var scores = {"ada": 10, "grace": 12, "alan": 9};
var names = keys(scores);
sort(names);
for (var name in names) {
    print(name, scores[name]);
}
```

## Next

- [Functions and Closures](@guide/functions-and-closures) — the other half of program structure.
- [Arrays](@guide/arrays) and [Maps](@guide/maps) — the collections these loops walk.
- [Coroutines and Channels](@guide/coroutines-and-channels) — concurrency that uses these same loops.