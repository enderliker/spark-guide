Variables are introduced with `var`; immutable bindings use `const`.

```spark
var count = 0;
const answer = 42;

count += 1;
print(count, answer);   // 1 42
```

Naming rules: an identifier starts with a letter (Unicode letters such as `ñ`
are allowed), `_` or a valid UTF-8 continuation byte, and continues with
letters, digits and `_`.

## Declaration forms

```spark
var name;                // nil
var name = "Ada";
const pi2 = 3.14159;     // initializer is required

var [first, second] = [1, 2];        // array destructuring
var {x, y} = {"x": 10, "y": 20};     // map destructuring
```

- `var name;` creates the binding with the value `nil`.
- `const` requires an initializer. Redefining the name is an error, and
  reassigning it is a compile error when the declaration is already visible.
  Inside a function compiled before the constant, the same mistake is caught at
  runtime instead.
- A `const` binding is immutable, but the value is not frozen: a `const` array
  or map can still be mutated.

```spark
const config = {"retries": 3};
config["retries"] = 5;      // allowed — the binding is constant, not the map
config = {};                // ConstError
```

## Scope

At the top level of a program, variables are globals. Inside a block or a
function they are locals.

```spark
var global = 1;

{
    var local = 2;
    print(global + local);   // 3
}

// print(local);             // NameError: local is out of scope
```

Blocks create a new lexical scope. An inner declaration shadows an outer one,
and the outer value reappears when the block ends:

```spark
var value = "outer";

{
    var value = "inner";
    print(value);     // inner
}

print(value);         // outer
```

::: warning Locals cannot see themselves
Reading a local variable inside its own initializer is a compile error:

```spark
var x = x + 1;   // CompileError
```

A nonexistent global, by contrast, is a runtime `NameError`.
:::

## Assignment

Assignment is a **statement**, not an expression:

```spark
x = 10;
x += 1;          // x = x + 1
x -= 2;
x *= 3;
x /= 2;
x %= 4;
bits &= mask;    // also |= ^= <<= >>=
cache ??= {};    // assign only when the target is nil

array[0] = 5;
array[1] += 10;
map["key"] = 42;
instance.field = 3;
```

The left-hand side must be a variable, an indexing expression or an instance
field. `print(x = 1)` and `print(x += 1)` are syntax errors, and chained
assignments (`a = b = c`) are not available.

`++` and `--` are the exception: they are expressions, run before or after the
value is read, and work on variables and array/map elements.

```spark
var i = 0;
print(i++, i, ++i);    // 0 1 2

var counts = {"a": 1};
counts["a"]++;
print(counts);         // {"a": 2}
```

An instance field is not a valid target for `++` or `--`; write
`instance.field += 1` instead.

## Globals and modules

Every top-level `var`, `const`, `fn` and `class` is global. Imported modules
share the same global namespace, so their top-level declarations become
directly available to the importer. This is convenient and worth knowing
before you split a large program across files; see
[Modules](@guide/modules).

```spark
import "./math_utils";

print(add(2, 3));     // add was declared at the top level of math_utils
```

## Shadowing and the linter

Shadowing is legal, but it is easy to do by accident. The built-in linter
reports it:

```bash
spark --lint program.spark
```

```text
program.spark:7:9: warning [shadowed-variable]: variable 'value' shadows an outer declaration
```

Names that begin with `_` are ignored by the unused-variable check, which makes
them a conventional way to say "deliberately unused". See
[Formatter and Linter](@tooling/formatter-and-linter).

## At a glance

| Form | Meaning |
| --- | --- |
| `var x = 1;` | Mutable local or global. |
| `var x;` | Mutable binding initialized to `nil`. |
| `const X = 1;` | Immutable binding, required initializer. |
| `var [a, b] = arr;` | Array destructuring. |
| `var {x, y} = map;` | Map destructuring by key. |
| `x = value;` | Assignment statement (not an expression). |
| `x += value;` | Compound assignment; `??=` assigns only when `nil`. |
| `x++;` / `--x;` | Increment and decrement expressions. |