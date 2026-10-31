Functions are values: they can be stored in variables, passed to other
functions and returned from them.

```spark
fn add(a, b) {
    return a + b;
}

var double = fn(x) { return x * 2; };

print(add(2, 3));       // 5
print(double(4));       // 8
```

## Declaration forms

```spark
fn named(a, b) { return a + b; }      // declaration
var anonymous = fn(a, b) { return a - b; };
var short_lambda = fn(x) => x * x;    // expression body
```

A short lambda is exactly equivalent to a one-expression function:

```spark
var square = fn(x) => x * x;
print(square(7));                 // 49
print((fn(x) => x * 2)(5));       // 10 — immediately invoked
```

The body of a short lambda must be an expression. `fn(x) => { ... }` is a
syntax error because `{` starts a map literal; use the full `fn(x) { ... }`
form for statement bodies.

A function without a `return` returns `nil`. A bare `return;` is allowed.

## Default parameters

Trailing parameters may have defaults. Default expressions are evaluated per
call and can reference earlier parameters.

```spark
fn greet(name, greeting = "Hello", punctuation = "!") {
    return greeting + ", " + name + punctuation;
}

print(greet("Ada"));             // Hello, Ada!
print(greet("Ada", "Hi"));       // Hi, Ada!
print(greet("Ada", "Hi", "."));  // Hi, Ada.
```

- Parameters without defaults cannot follow one with a default.
- The default is re-evaluated on every call, so it can allocate.
- Defaults also work in short lambdas: `fn(x, y = 2) => x * y`.

## Varargs

`...name` collects extra arguments into an array. It must be the last
parameter and cannot have a default.

```spark
fn sum_all(first, ...rest) {
    var total = first;
    for (var value in rest) {
        total += value;
    }
    return total;
}

print(sum_all(1));              // 1
print(sum_all(1, 2, 3, 4));     // 10
```

## Spread calls

`...` also unpacks an array into arguments:

```spark
fn add3(a, b, c) { return a + b + c; }

var args = [1, 2, 3];
print(add3(...args));           // 6
print(add3(1, ...[2, 3]));      // 6
```

Spreading a non-array value raises a `TypeError`. The same operator spreads an
array into an array literal: `[0, ...args, 4]`.

## Tail-call optimization

A call in tail position reuses the current call frame, so tail recursion runs
in constant stack space:

```spark
fn countdown(n, acc) {
    if (n == 0) {
        return acc;
    }
    return countdown(n - 1, acc + n);   // tail call
}

print(countdown(100000, 0));   // 5000050000
```

TCO applies to `return f(args);`, `return f(...args);` and calls in the
branches of a ternary (`return cond ? f() : g();`). Non-tail recursion is
bounded by the frame limit (4096 by default); exceeding it raises
`RecursionError`.

::: note
`return <native>(...)` is compiled as an ordinary call, because a reused frame
could not deliver a suspended network result. This matters only for internals;
it is still a normal return from your point of view.
:::

## Closures

A closure captures the **variable**, by reference. Two closures created in the
same call share that variable's state.

```spark
fn make_counter() {
    var total = 0;
    return fn(increment) {
        total += increment;
        return total;
    };
}

var counter = make_counter();
print(counter(5), counter(3));   // 5 8
```

A closure keeps its variables alive after the creating function returns. The
garbage collector traces captured values, so this is safe even under `gc()`.

### Closing over the loop variable

The variable of `for (var i = ...)` is a single variable for the whole loop.
A variable declared inside the body is new on each iteration:

```spark
var shared = [];
var fresh = [];

for (var i = 0; i < 3; i += 1) {
    var value = i;
    push(shared, fn() { return i; });
    push(fresh, fn() { return value; });
}

print(shared[0](), shared[1](), shared[2]());   // 3 3 3
print(fresh[0](), fresh[1](), fresh[2]());      // 0 1 2
```

If you need the index captured per iteration, copy it into a body-local
variable first.

## Higher-order functions

The standard library accepts functions as callbacks. A native is a function
value too, so it can be passed directly.

```spark
var numbers = [1, 2, 3, 4, 5];

print(map(numbers, fn(x) => x * x));          // [1, 4, 9, 16, 25]
print(filter(numbers, fn(x) => x % 2 == 0)); // [2, 4]
print(reduce(numbers, fn(acc, x) => acc + x, 0)); // 15
print(map(numbers, str));                      // ["1", "2", "3", "4", "5"]
```

`sort_by` takes a comparator that returns truthy when the first argument must
come before the second:

```spark
var people = [{"name": "Ada", "age": 36}, {"name": "Alan", "age": 41}];
sort_by(people, fn(a, b) => a.age < b.age);
```

The full set is documented in [Collections](@stdlib/collections).

::: warning Callbacks and suspension
Callbacks run at a deeper `run_depth`, so `yield`, a blocking channel
operation or a would-block socket call inside a callback raises a
`RuntimeError` instead of suspending. Collect what you need first, then do the
blocking work in the coroutine body.
:::

## Function arity

Calling a function with the wrong number of arguments raises `ArityError`.
Default parameters and varargs relax the count: a function with defaults has a
minimum arity, and a varargs function accepts any extra arguments.

```spark
fn f(a, b = 2) { return a + b; }
f(1);        // ok
f();         // ArityError
f(1, 2, 3);  // ArityError
```

`spawn` validates the arity at the `spawn` call itself, before the coroutine
is queued.

## Limits

- At most 255 parameters and arguments per call.
- At most 1024 local variables per function.
- At most 4096 ordinary call frames; tail calls reuse frames and are
  unconstrained.

See [Limits and Performance](@internals/limits-and-performance).

## Next

- [Arrays](@guide/arrays) — the collection most callbacks operate on.
- [Classes and Objects](@guide/classes-and-objects) — methods are functions with a receiver.
- [Coroutines and Channels](@guide/coroutines-and-channels) — functions as scheduled tasks.