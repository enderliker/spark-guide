Maps associate keys with values. Keys can be any value; values can be
anything, including other maps and functions.

```spark
var person = {"name": "Ada", "age": 36};
print(person["name"]);        // Ada
print(len(person));           // 2
```

## Literals

```spark
var empty = {};
var config = {
    "host": "127.0.0.1",
    "port": 8080,
    "tls": false,
    "headers": {"Accept": "application/json"},
};
```

Trailing commas are allowed. Keys may be arbitrary expressions; string keys are
the common case.

## Reading and writing

```spark
var person = {"name": "Ada", "age": 36};

person["age"] += 1;              // 37
person["city"] = "London";       // create a new key
print(person["missing"]);        // nil — missing keys are not an error

print(has(person, "age"));       // true
print(has(person, "height"));    // false
print(del(person, "city"));      // true
print(person);                   // {"name": "Ada", "age": 37}
```

Reading a missing key returns `nil`. This makes `map[key] ?? default` and
`get(map, key, default)` safe.

## Key equality

Keys follow the same equality rules as `==`:

- Numbers compare by value, and whole floats are canonicalized to integers, so
  `map[1]` and `map[1.0]` are the same key.
- Strings compare by content.
- Arrays, maps, functions and instances compare by identity, so two equal
  literals are different keys.

```spark
var m = {};
m[1] = "one";
print(m[1.0]);           // one
m[[1, 2]] = "array";
print(has(m, [1, 2]));   // false — a different array object
```

## Reference semantics

Maps are objects; assignment copies the reference:

```spark
var a = {"x": 1};
var b = a;
b["x"] = 2;
print(a["x"]);            // 2

var c = copy(a);          // shallow copy
c["x"] = 3;
print(a["x"], c["x"]);    // 2 3
```

`copy` is shallow. See [Types and Values](@guide/types-and-values).

## Helpers

```spark
var m = {"a": 1, "b": 2};

print(keys(m));              // ["a", "b"] in some order
print(values(m));            // [1, 2] in the same order
print(get(m, "a"));          // 1
print(get(m, "z", 0));       // 0
print(contains(m, "b"));     // true

merge(m, {"b": 20, "c": 30});
print(m);                    // {"a": 1, "b": 20, "c": 30} — src wins

clear(m);
print(len(m));               // 0
```

`keys` and `values` return new arrays. Their order should be treated as
unspecified; sort when output order matters.

## Iteration and destructuring

`for-in` over a map yields its keys:

```spark
var prices = {"apple": 10, "pear": 20};
for (var product in prices) {
    print(product, prices[product]);
}
```

Map destructuring binds by key:

```spark
var {name, age} = {"name": "Ada", "age": 36, "city": "London"};
print(name, age);   // Ada 36
```

Useful for request/response shapes and for options maps.

## Maps as objects

A function stored in a map becomes a method when called with dot syntax. The
receiver is bound to `self`:

```spark
var counter = {
    "count": 0,
    "increment": fn(step = 1) {
        self.count += step;
        return self.count;
    },
};

print(counter.increment(2));   // 2
print(counter.count);          // 2
```

Dot access also reads and writes fields:

```spark
counter.count = 10;
print(counter["count"]);       // 10
counter.increment();
print(counter.count);          // 11
```

Calls can chain because the method can return `self` or another method's
result:

```spark
var pipeline = {
    "value": 1,
    "add": fn(n) { self.value += n; return self; },
    "get": fn() { return self.value; },
};

print(pipeline.add(2).add(3).get());   // 6
```

::: warning `self` needs a receiver
If a function that uses `self` is called directly — `counter.increment` is
fine, but calling the function value without a receiver is not — the VM raises
a `NameError` saying `self` is not bound. Method syntax is what provides the
receiver.
:::

Inside a method, `self.field` works for any key, but a string key always reads
a field before an `__index__` method runs, and `a["name"] = value` always
writes a field. This keeps `self.x` usable inside index methods. See
[Classes and Objects](@guide/classes-and-objects#operator-overloading).

## Method syntax on maps

Map helpers have method forms with a shorter name in one case:

| Function | Method |
| --- | --- |
| `keys(m)` | `m.keys()` |
| `values(m)` | `m.values()` |
| `len(m)` | `m.len()` |
| `has(m, k)` | `m.has(k)` |
| `get(m, k, default?)` | `m.get(k, default?)` |
| `del(m, k)` | `m.delete(k)` |
| `clear(m)` | `m.clear()` |
| `merge(m, src)` | `m.merge(src)` |

```spark
var user = {"name": "Ada", "role": "admin"};
print(user.has("role"), user.get("email", "none"));   // true none
user.delete("role");
```

## Recipes

### Grouping

```spark
fn group_by(values, key_fn) {
    var groups = {};
    for (var value in values) {
        var key = key_fn(value);
        if (!has(groups, key)) {
            groups[key] = [];
        }
        push(groups[key], value);
    }
    return groups;
}

var people = [
    {"name": "Ada", "team": "core"},
    {"name": "Alan", "team": "core"},
    {"name": "Grace", "team": "tools"},
];

print(group_by(people, fn(p) => p.team));
// {"core": [...], "tools": [...]}
```

### Counting

```spark
fn frequencies(text) {
    var counts = {};
    for (var character in text) {
        counts[character] = (counts[character] ?? 0) + 1;
    }
    return counts;
}

print(frequencies("spark"));
// {"s": 1, "p": 1, "a": 1, "r": 1, "k": 1} in some order
```

### Merging with defaults

`merge` overwrites, so put the defaults first:

```spark
fn with_defaults(options) {
    var merged = {"timeout_ms": 5000, "follow_redirects": true};
    return merge(merged, options);
}

print(with_defaults({"timeout_ms": 1000}).timeout_ms);   // 1000
print(with_defaults({}).follow_redirects);               // true
```

## Maps versus classes

Maps-as-objects are convenient for ad-hoc records and method bags. For types
with a constructor, inheritance and static members, use
[classes](@guide/classes-and-objects). Both can be mixed: an instance field can
hold a map, and a map can hold instance references.

## Next

- [Strings](@guide/strings) — the other workhorse value type.
- [Classes and Objects](@guide/classes-and-objects) — nominal types with inheritance.
- [Collections](@stdlib/collections) — the complete native list.