# GREEN-1 — Device-Model Binding Check

**Branch:** `research/semantic-continuity-green1`  
**Baseline:** `334363d4befdae9a3c31675c8feab0fe0214aa57`

## Result

GREEN-1 closes the exact binding gap demonstrated by RED-1.

RED-1 established:

```text
capability declaration + successful lowering
                 ≠
binding correctness
```

because both of these mappings were accepted:

```text
SemanticId(1001) -> 0x20
SemanticId(1001) -> 0x21
```

GREEN-1 adds one missing formal object:

```text
DeviceModel(Resource)
    denotes : Resource -> Option SemanticId
```

and one executable relation:

```text
checkBinding(device, resourceOf, semanticId)
```

The realization supplies `resourceOf`.  
The independently stated device model supplies `denotes`.

A binding is accepted only when both agree on semantic identity.

## Why the physical address is allowed in DeviceModel

The target-neutral contract still contains only:

```text
statusIdentity = SemanticId(1001)
statusScript   = WRITE(destination = statusIdentity)
```

It does **not** contain `0x20`.

For the PVM32 target, the device model states target-specific facts:

```text
0x20 denotes SemanticId(1001)
0x21 denotes SemanticId(1002)
```

That is the intended abstraction boundary:

```text
target-neutral meaning
        |
        v
target-specific device model
        |
        v
physical resource representation
```

Moving the physical fact into the device model is not hiding it. The address is
a target fact and therefore belongs at the target boundary.

## Machine-checked result

`lean/PSL/SemanticContinuityGreen1.lean` proves:

```text
old gate(reference)   = true
old gate(adversarial) = true

new binding check(reference)   = true
new binding check(adversarial) = false
```

It also proves generically:

```text
checkBinding(device, resourceOf, id) = true
    <->
bindingMatchesDevice(device, resourceOf, id)
```

So the executable checker is sound and complete for the relation GREEN-1
actually claims.

## What GREEN-1 does not prove

This is **not** yet full realization soundness.

The device model currently says only what a resource denotes. It does not yet
model:

- numeric representation or scale;
- engineering units;
- byte order or signedness;
- configuration/authority state;
- command ordering;
- ACK/NACK behavior;
- persistence;
- atomicity;
- timing;
- simulator or physical-device conformance.

A realization that uses the correct resource but writes the wrong value can
still pass GREEN-1.

That limitation is intentional.

## Trust boundary

GREEN-1 removes trust in the realization's binding declaration itself.

It does **not** remove trust in the stated `DeviceModel`.

The theorem is therefore:

> accepted binding is faithful **with respect to the stated device model**.

Whether that model matches QEMU, Renode, firmware, or physical hardware remains
a separate conformance obligation.

## Why this is the minimum useful GREEN

We considered introducing all of:

```text
Realization
RealizationEvidence
Observation
Trace
Checker
Evolution
```

GREEN-1 does not need them.

For the RED-1 counterexample, the smallest missing distinction is an
independent target model of resource meaning.

Adding more theory before a failing case requires it would make the research
architecture larger without increasing the result.

## Next falsification target

The natural RED-2 is:

> use the **correct resource** but the **wrong representation**.

For example:

```text
semantic intent: 25.0 °C
correct target encoding: 250
adversarial encoding:    25
resource:                0x20 in both cases
```

Both bindings would pass GREEN-1.

If we can machine-check that failure without changing the semantic contract,
then RED-2 will justify the next layer of device behavior/observation theory.

## Kill condition retained

If future work requires target addresses, encodings, or protocol mechanics to
be inserted into the target-neutral semantic contract, the continuity
abstraction has failed and should be redesigned rather than patched.
