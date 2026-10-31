This page lists every array and map native, including the higher-order
helpers. The language-level guides are [Arrays](@guide/arrays) and
[Maps](@guide/maps).

## Arrays

| Call | Result |
| --- | --- |
| `len(a)` | Number of elements. |
| `push(a, value)` | Appends and returns the array. |
| `pop(a)` | Removes and returns the last element; error if empty. |
| `insert(a, index, value)` | Inserts at `index`; returns the array. |
| `remove(a, index)` | Removes and returns the element at `index`. |
| `reverse(a)` | Reverses in place; returns the array. |
| `fill(a, value)` | Sets every element to `value`; returns the array. |
| `slice(a, start, end?)` | New array for `[start, end)` with clamping. |
| `range(n)` / `range(start, end)` | Array of integers in `[start, end)`. |
| `contains(a, value)` | Membership by `==`. |
| `index_of(a, value)` | First index, or `-1`. |
| `sort(a)` | Stable in-place sort of numbers or strings. |
| `sort_by(a, fn)` | Stable in-place sort with a comparator. |
| `map(a, fn)` / `filter(a, fn)` | Transform / select into a new array. |
| `reduce(a, fn, initial?)` | Left fold with `fn(acc, x)`. |
| `each(a, fn)` | Calls `fn(x)` for each element; returns `nil`. |
| `any(a, fn?)` / `all(a, fn?)` | Truthiness or predicate over the elements. |
| `sum(a)` | Sum of numeric elements. |
| `enumerate(a)` | `[[index, value], ...]`. |
| `zip(a, b)` | `[[a[i], b[i]], ...]` up to the shorter array. |
| `join(a, sep)` | Joins stringified elements. |

```spark
var a = [3, 1, 2];

print(len(a));             // 3
print(a.len());            // 3
print(contains(a, 2));     // true
print(index_of(a, 1));     // 1

push(a, 4);
print(a);                  // [3, 1, 2, 4]
print(pop(a));             // 4
print(a);                  // [3, 1, 2]

insert(a, 0, 9);
print(a);                  // [9, 3, 1, 2]
print(remove(a, 1));       // 3
print(a);                  // [9, 1, 2]
```

### range

```spark
print(range(5));           // [0, 1, 2, 3, 4]
print(range(2, 6));        // [2, 3, 4, 5]
print(range(0));           // []
```

`range(start, end)` is exclusive at the end and returns `[]` when `start >=
end`.

### sort and sort_by

```spark
var numbers = [10, 2, 33, 4];
sort(numbers);
print(numbers);            // [2, 4, 10, 33]

var words = ["pear", "fig", "banana"];
sort_by(words, fn(a, b) => len(a) < len(b));
print(words);              // ["fig", "pear", "banana"]
```

- `sort` accepts only all-numbers or all-strings; mixing types is an error.
- The sort is a stable merge sort, O(n log n).
- `sort_by`'s comparator returns truthy when `a` must come before `b`.
- Both sort in place and return the array.
- Membership and default sorting use primitive equality and ordering, not
  `__eq__` / `__lt__`, for instances.

### Higher-order helpers

```spark
var numbers = [1, 2, 3, 4, 5];

print(map(numbers, fn(x) => x * 2));              // [2, 4, 6, 8, 10]
print(filter(numbers, fn(x) => x % 2 == 1));      // [1, 3, 5]
print(reduce(numbers, fn(acc, x) => acc + x, 0)); // 15
print(reduce(numbers, fn(acc, x) => acc + x));    // 15 (first element is the seed)

each(numbers, fn(x) { print(x); });               // 1 2 3 4 5
print(any(numbers, fn(x) => x > 4));              // true
print(all(numbers, fn(x) => x > 0));              // true
print(any([0, nil, false]));                      // true — 0 is truthy
print(all([1, "x", []]));                         // true
print(sum(numbers));                              // 15
print(enumerate(["a", "b"]));                     // [[0, "a"], [1, "b"]]
print(zip([1, 2], ["a", "b", "c"]));              // [[1, "a"], [2, "b"]]
```

- `reduce` without `initial` uses the first element as the accumulator and
  starts at the second.
- `any` / `all` without a predicate test truthiness.
- `sum` returns an integer when every element is an integer.
- `map`, `filter`, `reduce`, `each`, `any`, `all` and `sort_by` accept a
  closure or another native (`map(numbers, str)`).
- Callbacks cannot suspend a coroutine. See
  [Functions and Closures](@guide/functions-and-closures).

::: warning Callback arity
`map`, `filter`, `each`, `any`, `all` and `sort_by` call their callback with a
fixed arity. `sort_by` calls `fn(x, y)`; the others call `fn(x)` (and
`reduce` calls `fn(acc, x)`). A mismatched callback raises `ArityError`.
:::

## Maps

| Call | Result |
| --- | --- |
| `len(m)` | Number of keys. |
| `has(m, key)` | Whether the key exists. |
| `del(m, key)` | Deletes the key; returns whether it existed. |
| `keys(m)` | Array of keys. |
| `values(m)` | Array of values, in the corresponding order. |
| `get(m, key, default?)` | Value for the key, or the default / `nil`. |
| `clear(m)` | Empties the map; returns it. |
| `merge(dest, src)` | Copies `src` into `dest`; `src` wins. Returns `dest`. |
| `contains(m, key)` | Same membership test as `has`. |

```spark
var m = {"a": 1, "b": 2};

print(len(m));                  // 2
print(has(m, "a"));             // true
print(contains(m, "z"));        // false
print(get(m, "b"));             // 2
print(get(m, "z", 0));          // 0

print(del(m, "a"));             // true
print(del(m, "a"));             // false
print(keys(m));                 // ["b"]

merge(m, {"b": 20, "c": 30});
print(m);                       // {"b": 20, "c": 30}

clear(m);
print(m);                       // {}
```

Method forms use `delete` instead of `del`:

```spark
var user = {"name": "Ada"};
print(user.has("name"), user.get("role", "unknown"));   // true unknown
user.delete("name");
print(user.len());                                       // 0
```

### Iteration order

`keys` and `values` return arrays in the map's internal order. That order is an
implementation detail; sort the keys when the order matters.

```spark
var counts = {"b": 2, "a": 1};

var names = keys(counts);
sort(names);
for (var name in names) {
    print(name, counts[name]);
}
```

## Shared semantics

- Arrays and maps are reference values; `copy` is shallow.
- Indexing is exact and raises `IndexError` when out of range; slicing clamps.
- `len` on an instance calls `__len__`.
- `contains` and `index_of` also work on strings (substring / character
  position).
- `in` uses the same rules as `contains`.

```spark
print("a" in {"a": 1});     // true
print(2 in [1, 2]);         // true
print("ar" in "spark");     // true
```

## Common patterns

### Mapping over a map

```spark
var prices = {"apple": 10, "pear": 20};

var expensive = {};
for (var name in prices) {
    if (prices[name] >= 15) {
        expensive[name] = prices[name];
    }
}
print(expensive);           // {"pear": 20}
```

### Transposing rows and columns

```spark
fn transpose(matrix) {
    var rows = len(matrix);
    if (rows == 0) {
        return [];
    }
    var result = [];
    for (var column = 0; column < len(matrix[0]); column += 1) {
        var line = [];
        for (var row = 0; row < rows; row += 1) {
            push(line, matrix[row][column]);
        }
        push(result, line);
    }
    return result;
}

print(transpose([[1, 2, 3], [4, 5, 6]]));
// [[1, 4], [2, 5], [3, 6]]
```

### Flattening one level

```spark
fn flatten(lists) {
    var result = [];
    for (var list in lists) {
        for (var value in list) {
            push(result, value);
        }
    }
    return result;
}

print(flatten([[1, 2], [3], []]));   // [1, 2, 3]
```

### Stable ranking

```spark
fn rank(values) {
    var pairs = [];
    for (var i = 0; i < len(values); i += 1) {
        push(pairs, {"value": values[i], "index": i});
    }
    sort_by(pairs, fn(a, b) => a.value < b.value);

    var ranks = fill(range(len(values)), 0);
    for (var position = 0; position < len(pairs); position += 1) {
        ranks[pairs[position].index] = position + 1;
    }
    return ranks;
}

print(rank([30, 10, 20]));   // [3, 1, 2]
```

## Next

- [Numbers and Math](@stdlib/numbers-and-math) — numeric helpers.
- [Files, System and Data](@stdlib/files-and-system) — JSON serialization of collections.
- [Arrays](@guide/arrays) and [Maps](@guide/maps) — the language-level guides.