Arrays are ordered, mutable sequences of values. They can hold anything,
including other arrays, maps and functions.

```spark
var languages = ["Spark", "C", "Lua"];
print(languages);            // ["Spark", "C", "Lua"]
print(len(languages));       // 3
print(languages[0]);         // Spark
```

## Literals and nesting

```spark
var empty = [];
var mixed = [1, "two", true, nil, [3, 4], {"k": 5}];
var matrix = [
    [1, 2, 3],
    [4, 5, 6],
];
```

Trailing commas are allowed. A single array literal may contain at most 255
elements.

## Spread

`...` inlines the elements of another array:

```spark
var first = [1, 2];
var all = [0, ...first, 3];
print(all);                  // [0, 1, 2, 3]
```

See also [spread calls](@guide/functions-and-closures#spread-calls).

## Indexing

Indexes must be integers. A negative index counts from the end. An index
outside the range is a runtime `IndexError`, and the message names the index
you wrote.

```spark
var a = [10, 20, 30];
print(a[0], a[1], a[-1]);    // 10 20 30
a[1] = 25;
a[0] += 5;
print(a);                    // [15, 25, 30]

// a[3]   -> IndexError: index 3 is out of range
// a[-4]  -> IndexError: index -4 is out of range
```

## Slicing

`a[start:end:step]` returns a **new** array with the elements in
`[start, end)`, taking every `step`-th element. Every part is optional.
Negative positions count from the end and out-of-range positions are clamped.

```spark
var a = [1, 2, 3, 4, 5];

print(a[1:3]);      // [2, 3]
print(a[:2]);       // [1, 2]
print(a[2:]);       // [3, 4, 5]
print(a[:]);        // [1, 2, 3, 4, 5] — a copy
print(a[::2]);      // [1, 3, 5]
print(a[::-1]);     // [5, 4, 3, 2, 1]
print(a[10:20]);    // [] — clamped, no error
```

The step must not be `0`. A slice is a value, not a place: `a[1:3] = x` is a
syntax error. The `slice(array, start, end?)` native does the same without a
step.

## Mutation and reference semantics

Arrays are objects, so assignment copies the reference:

```spark
var a = [1, 2, 3];
var b = a;
push(b, 4);
print(a);          // [1, 2, 3, 4]

var c = copy(a);   // shallow copy
push(c, 5);
print(a);          // [1, 2, 3, 4]
print(c);          // [1, 2, 3, 4, 5]
```

`copy` is shallow; nested collections remain shared.

## Growing and shrinking

```spark
var stack = [];

push(stack, 1);              // returns the array
push(stack, 2);
push(stack, 3);
print(pop(stack));           // 3
print(stack);                // [1, 2]

insert(stack, 0, "first");   // insert at index
print(stack);                // ["first", 1, 2]

print(remove(stack, 1));     // 1
print(stack);                // ["first", 2]
```

`pop` and `remove` return the removed element. `pop` on an empty array is an
error; `remove` with an out-of-range index is an `IndexError`.

## Searching and reordering

```spark
var values = [3, 1, 2];

print(contains(values, 2));      // true
print(index_of(values, 1));      // 1
print(index_of(values, 99));     // -1

reverse(values);
print(values);                   // [2, 1, 3]

sort(values);
print(values);                   // [1, 2, 3]

fill(values, 0);
print(values);                   // [0, 0, 0]
```

`sort` sorts numbers or strings in place using a stable merge sort. Mixing
numbers and strings is an error. Pass a comparator for any other ordering —
`sort_by` is the same call:

```spark
var words = ["pear", "fig", "banana"];
sort_by(words, fn(a, b) => len(a) < len(b));
print(words);                    // ["fig", "pear", "banana"]

print(sort([3, 1, 2], fn(a, b) { return a > b; }));   // [3, 2, 1]
```

The comparator returns truthy when `a` must come before `b`. Sorting is stable.

## Iteration

```spark
var total = 0;
for (var value in [1, 2, 3]) {
    total += value;
}

for (var index, value in ["a", "b"]) {
    print(index, value);         // 0 a / 1 b
}
```

See [Control Flow](@guide/control-flow#for-in).

## Higher-order helpers

```spark
var numbers = [1, 2, 3, 4, 5, 6];

print(map(numbers, fn(x) => x * 2));            // [2, 4, 6, 8, 10, 12]
print(filter(numbers, fn(x) => x % 2 == 0));    // [2, 4, 6]
print(reduce(numbers, fn(acc, x) => acc + x, 0)); // 21
print(any(numbers, fn(x) => x > 5));            // true
print(all(numbers, fn(x) => x > 0));            // true
print(sum(numbers));                            // 21
print(enumerate(["a", "b"]));                   // [[0, "a"], [1, "b"]]
print(zip([1, 2], ["a", "b"]));                  // [[1, "a"], [2, "b"]]
```

`map`, `filter`, `each`, `reduce`, `any`, `all` and `sort_by` accept a closure
or another native. The callbacks cannot suspend a coroutine; see the warning
in [Functions and Closures](@guide/functions-and-closures).

## Destructuring

```spark
var pair = [10, 20];
var [first, second] = pair;
print(first, second);      // 10 20
```

Extra elements are ignored; missing ones become `nil`. For indexed iteration
use the two-variable form `for (var i, value in array)`, described in
[Control Flow](@guide/control-flow#for-in).

## Method syntax

Array natives can also be called as methods:

```spark
var a = [3, 1, 2];

print(a.len());                    // 3
print(a.sort());                   // [1, 2, 3]
print(a.map(fn(x) => x * 10));      // [10, 20, 30]
print([1, 2].join("+"));            // 1+2
print(a.contains(2));               // true
```

See [Collections](@stdlib/collections) for the complete list.

## Recipes

### Deduplicating while preserving order

```spark
fn unique(values) {
    var seen = {};
    var result = [];
    for (var value in values) {
        if (has(seen, value)) {
            continue;
        }
        seen[value] = true;
        push(result, value);
    }
    return result;
}

print(unique([1, 2, 1, 3, 2]));   // [1, 2, 3]
```

### Chunking

```spark
fn chunk(values, size) {
    var chunks = [];
    for (var i = 0; i < len(values); i += size) {
        push(chunks, values[i:i + size]);
    }
    return chunks;
}

print(chunk([1, 2, 3, 4, 5], 2));   // [[1, 2], [3, 4], [5]]
```

### Building a matrix

```spark
fn zeros(rows, columns) {
    var grid = [];
    for (var r = 0; r < rows; r += 1) {
        push(grid, fill(range(columns), 0));
    }
    return grid;
}

var grid = zeros(2, 3);
grid[1][2] = 7;
print(grid);   // [[0, 0, 0], [0, 0, 7]]
```

::: warning Shared rows
`var row = fill(range(3), 0); var grid = [row, row];` creates two references to
the same row. Call `range(columns)` / `fill` inside the loop to get
independent rows, as above.
:::

## Next

- [Maps](@guide/maps) — keyed collections and objects.
- [Strings](@guide/strings) — slicing and building text.
- [Collections](@stdlib/collections) — the complete native reference.