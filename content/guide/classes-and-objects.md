Spark has two object models that work together: maps with functions act as
lightweight objects, and `class` declarations create nominal types with
inheritance. This page covers classes. The map form is described in
[Maps](@guide/maps#maps-as-objects).

## Declaring a class

```spark
class Person {
    var greeting = "Hello";     // field with a default value

    init(name, age = 0) {
        self.name = name;
        self.age = age;
    }

    greet() {
        return self.greeting + ", I am " + self.name;
    }
}

var person = new Person("Ada", 36);
print(person.greet());          // Hello, I am Ada
print(person.age);              // 36
person.age += 1;                // 37
```

- Fields may be declared with `var name = expression;`; the initializer is
  optional and defaults to `nil`.
- Fields are initialized **base-first**, before `init` runs, and every instance
  receives its own copy.
- Fields can also be created dynamically by assigning to `self.name`; they do
  not need to be declared.
- `init` is optional. When present, it is the constructor body.
- Methods are ordinary functions attached to the class.

## Construction

Construction always uses `new`:

```spark
var p = new Person("Ada");     // runs init
```

Calling the class without `new` is a `TypeError` that tells you to use `new`:

```text
TypeError: 'Person' is a class; use 'new Person(...)' to create an instance
```

`init` implicitly returns the new instance. A bare `return;` ends the
constructor early, but `return value;` inside `init` is a compile error.
`new` checks the argument count against `init`, including defaults and
varargs.

A class without `init` can still be constructed with `new ClassName()`; declared
fields are initialized and the object is returned.

## self

Inside any method called as `receiver.method(...)`, `self` refers to the
receiver.

```spark
class Counter {
    var total = 0;

    add(step) {
        self.total += step;
        return self;
    }
}

print(new Counter().add(2).add(3).total);   // 5
```

`self` is a normal local for nested functions and lambdas, so a callback
created inside a method can capture it:

```spark
class Timer {
    init() { self.ticks = 0; }

    schedule() {
        return fn() {
            self.ticks += 1;
            return self.ticks;
        };
    }
}
```

If a function that reads `self` is called without a receiver, the VM raises a
`NameError` saying `self` is not bound.

A field of an instance is not a valid target for `++`/`--`:

```spark
self.n++;          // runtime error
self.n = self.n + 1;   // correct
```

## Inheritance

```spark
class Animal {
    init(name) { self.name = name; }

    speak() { return self.name + " makes a sound"; }

    static kingdom() { return "Animalia"; }
}

class Dog extends Animal {
    init(name) {
        super(name);
        self.tricks = 0;
    }

    speak() { return self.name + " barks"; }

    parent_speak() { return super.speak(); }

    static kingdom() { return super.kingdom() + "/Canidae"; }
}

var dog = new Dog("Rex");
print(dog.speak());          // Rex barks
print(dog.parent_speak());   // Rex makes a sound
print(Dog.kingdom());        // Animalia/Canidae
```

- `extends` names a single superclass. A class without it has no superclass.
- `super(args)` calls the superclass `init` and is only valid inside an
  instance method.
- `super.method(args)` starts the lookup at the superclass instead of the
  receiver's class. It works in instance methods and in static methods.
- A subclass that does not define `init` inherits the closest one, and
  `new Sub(...)` runs it normally.
- Using `super` outside a class, or in a class without a superclass, is an
  error.

## Static fields and methods

```spark
class Config {
    static var level = 1;

    static describe() {
        return "level " + str(Config.level);
    }
}

print(Config.level);     // 1
Config.level = 5;
print(Config.describe()); // level 5
```

- `static var` and `static` methods belong to the class and are read or called
  as `Class.member`.
- Statics are inherited: a subclass reads a static defined by an ancestor.
  Assigning through a subclass (`Sub.value = 1`) creates a member on that
  subclass instead of modifying the ancestor.
- `self` is not bound in a static method. Calling a static on an instance, or
  an instance method on the class, raises an error that names the receiver.

## Type checks

```spark
class Animal {}
class Dog extends Animal {}

var dog = new Dog();

print(type(dog));                    // Dog
print(type(Dog));                    // class
print(dog instanceof Animal);        // true
print(dog instanceof Dog);           // true
print(nil instanceof Animal);        // false

print(is_a(dog, Animal));            // true
print(isinstance(dog, Animal));      // true
print(isinstance(dog, "Dog"));       // true — type-name string also works
```

- `type(instance)` returns the class name; `type(SomeClass)` is `"class"`.
- `instanceof` and `is_a` respect inheritance and require a class value.
- `isinstance` also accepts a type-name string (`"array"`, `"number"`, a class
  name) for compatibility with built-in types.
- Class names cannot collide with built-in type names such as `map` or
  `number`.

## Printing and `to_string`

```spark
class Point {
    init(x, y) { self.x = x; self.y = y; }

    to_string() { return "(${self.x}, ${self.y})"; }
}

var p = new Point(3, 4);
print(p);               // (3, 4)
print(str(p));          // (3, 4)
print("point ${p}");    // point (3, 4)
print([p]);             // [<Point instance>]
```

`to_string` must return a string. Without it, instances print as
`<ClassName instance>`. Collections always use the default representation for
nested instances, even when `to_string` is defined, to keep formatting
non-recursive.

## Operator overloading

Special methods give operators meaning for instances:

| Expression | Method |
| --- | --- |
| `a + b`, `a - b`, `a * b`, `a / b`, `a % b`, `a ** b` | `__add__`, `__sub__`, `__mul__`, `__div__`, `__mod__`, `__pow__` |
| `-a` | `__neg__()` |
| `a == b`, `a != b` | `__eq__(b)` |
| `a < b`, `a <= b`, `a > b`, `a >= b` | `__lt__`, `__le__`, `__gt__`, `__ge__` |
| `a[i]` | `__index__(i)` |
| `a[i] = value` | `__index_set__(i, value)` |
| `len(a)` | `__len__()` |
| `str(a)`, `print(a)`, `"${a}"` | `to_string()` |

```spark
class Vec {
    init(x, y) {
        self.x = x;
        self.y = y;
    }

    __add__(other) {
        return new Vec(self.x + other.x, self.y + other.y);
    }

    __eq__(other) {
        return (other instanceof Vec) and self.x == other.x and self.y == other.y;
    }

    __lt__(other) {
        return self.x < other.x;
    }

    __len__() {
        return 2;
    }

    __index__(i) {
        return i == 0 ? self.x : self.y;
    }

    to_string() {
        return "Vec(" + str(self.x) + ", " + str(self.y) + ")";
    }
}

var a = new Vec(1, 2);
var b = new Vec(3, 4);

print(a + b);       // Vec(4, 6)
print(a == new Vec(1, 2));   // true
print(a < b);       // true
print(len(a));      // 2
print(a[0], a[1]);  // 1 2
```

Rules that apply to every special method:

- Only the left operand's method is tried. Reflected variants (`__radd__` and
  friends) are not implemented; the right operand is consulted only for
  `__eq__`, when the left one does not define it.
- Comparison results use Spark truthiness, so returning `0` or `""` means
  false.
- `a == nil` and `nil == b` always use identity, even when the class defines
  `__eq__`, so nil checks stay reliable.
- A string key always addresses a field before `__index__` runs, and
  `a["name"] = value` always writes a field instead of calling
  `__index_set__`. This keeps `self.x` usable inside index methods. Other key
  types go to the index methods.
- `__len__` must return a non-negative integer.
- Membership (`in`), `contains`, `index_of` and the default `sort` use
  primitive equality and ordering, not `__eq__` and `__lt__`.

## Methods, fields and lookup

- A method is looked up on the instance's class and then up the superclass
  chain.
- A field shadows a method of the same name when read through `obj.field`.
- Calling a field that is not a function raises `TypeError: field 'x' is not a
  function`.
- Missing methods produce `NameError: method 'x' not found on ClassName`.

## A larger example

```spark
class Shape {
    static count = 0;

    init(name) {
        self.name = name;
        Shape.count += 1;
    }

    area() {
        return 0;
    }

    describe() {
        return "${self.name} with area ${self.area()}";
    }

    to_string() {
        return self.describe();
    }
}

class Rect extends Shape {
    init(width, height) {
        super("rect");
        self.width = width;
        self.height = height;
    }

    area() { return self.width * self.height; }
}

class Circle extends Shape {
    init(radius) {
        super("circle");
        self.radius = radius;
    }

    area() { return 3.14159 * self.radius ** 2; }
}

var shapes = [new Rect(3, 4), new Circle(2)];
for (var shape in shapes) {
    print(shape.describe());
}
print("created:", Shape.count);   // 2
```

The method call `self.area()` dispatches on the instance's class, so `Rect` and
`Circle` each run their own version while `describe` stays shared.

## Next

- [Errors and Exceptions](@guide/errors-and-exceptions) — throwing and catching.
- [Modules](@guide/modules) — sharing classes across files.
- [Collections](@stdlib/collections) — collection helpers that interact with `__len__` and `__index__`.