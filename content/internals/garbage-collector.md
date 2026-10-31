Spark uses a non-compacting mark-and-sweep collector. There is no reference
counting and no generational nursery in 0.1.0; the collector traces roots,
marks reachable objects and sweeps the rest.

## Roots

A collection starts from:

- the value stack;
- every frame's closure;
- the global slots and their names;
- the `global_names` table;
- open upvalues;
- the scheduler's network waiter list.

Everything reachable from a root survives. Blocked coroutines, their private
stacks and captured locals are traced, so `gc()` never breaks a pending
`send`, `receive` or `join`.

## Mark phase

An iterative traversal uses an explicit gray stack instead of C recursion, so
deep object graphs cannot overflow the C stack. Marking follows:

- function constants;
- array elements;
- map keys and values;
- upvalues;
- names;
- coroutine state and awaited resources.

Strings are interned globally, which matters for sweep: before unlinking dead
objects, unmarked strings are removed from the intern table, so a later
interning operation never returns a freed string.

## Sweep phase

`sweep` walks the intrusive list of all objects, unlinks unmarked ones and
calls `object_free`. Finalizers release external resources:

- `ObjFile` closes its `FILE *`;
- `ObjSocket` closes its descriptor (and TLS state);
- `ObjServer` closes its listening descriptor;
- `ObjWebSocket` frees its buffers and releases the transport.

Explicit `close()` is still preferred; finalization is a safety net, not a
substitute for deterministic resource management.

## Adaptive threshold

The next collection is triggered by a byte threshold computed from the
survival ratio of the last cycle:

| Survival | Next factor | Rationale |
| --- | --- | --- |
| > 70% | 2.5× | Most objects live; avoid thrashing. |
| < 30% | 1.5× | Most objects die; bound the footprint. |
| otherwise | 2.0× | Steady state. |

There is a 1 MiB minimum. `memory.c` accounts bytes, and allocation checks the
threshold. `gc()` runs a cycle immediately and updates the adaptive threshold,
which is useful in tests and benchmarks.

## GC safety rules

The collector is stopped during compilation because freshly created objects
have no root yet. Around constructions that allocate several blocks before the
object becomes visible, the VM pauses the collector or roots intermediates
explicitly.

The rule for native code:

> A fresh object is protected only while it is reachable from a root.

If a native creates an object and then hands it to a container, it must root it
first, because growing the container can trigger a collection. Natives push
temporaries on the value stack and pop them afterwards. A callback result that
is stored after `call_callback` returns must be rooted the same way.

The value stack itself grows dynamically: when it is reallocated, every
interior pointer — the stack top, each frame's `slots`, and open upvalues'
`location` — is rebased by the address delta.

## What the collector does not do

- It does not compact, so pointers into objects remain stable.
- It does not run concurrently; collection happens on the interpreter thread.
- It does not collect reference cycles specially: cycles are simply
  unreachable and swept like anything else, because tracing does not care about
  cycles.
- It does not have a generational nursery or an object arena in 0.1.0. Both are
  planned, incrementally and behind measurements, in the roadmap.

## Observing it

```spark
gc();                    // force a cycle now
print(clock());          // measure around allocation-heavy work
```

There is no public statistics API in 0.1.0. Benchmarks such as `gc_stress`,
`alloc` and `coroutine_gc` exercise collection under load; the test suite
asserts that live coroutines and captured values survive.

## Why this design

Mark and sweep is simple to reason about and safe in the presence of cycles,
which matters for a language with closures, maps and class instances that can
reference each other freely. A non-compacting collector keeps object addresses
stable, simplifying interning and the stack-rebasing scheme. The adaptive
threshold is a small, measurable knob that avoids both pathological thrashing
and unbounded growth without exposing tuning to programs.

## Next

- [Architecture](@internals/architecture) — where allocation sits in the pipeline.
- [Limits and Performance](@internals/limits-and-performance) — memory limits and benchmarks.
- [Coroutines and Channels](@guide/coroutines-and-channels) — why blocked coroutines are roots.