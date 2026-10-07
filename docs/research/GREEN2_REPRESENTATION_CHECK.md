# GREEN-2 — Target-Specific Representation Check

**Branch:** `research/semantic-continuity-green2`  
**Baseline:** `39dced4cb4a10fc7730eef06afeae474049a94b7`

## Result

GREEN-2 closes the exact representation gap demonstrated by RED-2.

RED-2 established:

```text
binding correctness
        !=
representation correctness
```

because two candidates used the same GREEN-1-correct resource while carrying
different raw values:

```text
resource = 0x20

reference raw = 250
mutated raw   = 25
```

GREEN-1 accepted both because it checked only resource denotation.

GREEN-2 adds one missing formal object:

```text
RepresentationModel(SemanticValue, Raw)
    encode : SemanticValue -> Option Raw
```

and one executable relation:

```text
checkRepresentation(model, semanticValue, raw)
```

## Target-neutral value

The witness now states the intended value independently of the target:

```text
setpoint25C:
    magnitude = 25
    unit      = Celsius
```

There is no PVM32 address, fixed-point scale, or raw value in this semantic
quantity.

## Target-specific representation

The PVM32 representation model states:

```text
Celsius magnitude n -> raw n * 10
Fahrenheit           -> unsupported
```

Therefore:

```text
25 °C -> 250
```

is derived from target-specific representation semantics rather than copied
into the target-neutral value.

## Machine-checked result

`lean/PSL/SemanticContinuityGreen2.lean` proves:

```text
GREEN1(reference) = true
GREEN1(mutated)   = true

Representation(reference raw 250) = true
Representation(mutated raw 25)    = false

GREEN2(reference) = true
GREEN2(mutated)   = false
```

It also proves generically:

```text
checkRepresentation(model, value, raw) = true
    <->
representationMatches(model, value, raw)
```

So the executable checker is sound and complete for the representation
relation GREEN-2 actually states.

## Separation of concerns

GREEN-2 keeps two target obligations distinct:

```text
semantic identity
      |
      v
DeviceModel
      |
      v
target resource

semantic value
      |
      v
RepresentationModel
      |
      v
raw payload
```

A candidate must satisfy both.

This matters because a correct address with an incorrect payload is still an
incorrect realization.

## What GREEN-2 does not prove

GREEN-2 is still **not** full realization soundness.

It does not yet model:

- required configuration/privilege state;
- command ordering;
- ACK/NACK semantics;
- persistence;
- atomicity;
- timing;
- simulator conformance;
- physical-device conformance.

The `DeviceModel` and `RepresentationModel` are stated model assumptions.
Future evidence must justify their relationship to executable and physical
targets.

## Why this remains minimal

GREEN-2 does not introduce traces, protocol automata, realization certificates,
or virtual hardware.

RED-2 required only one missing distinction: semantic value versus raw target
representation.

Adding protocol theory now would solve a problem that has not yet been
machine-demonstrated.

## Next falsification target

The natural RED-3 is:

> use the correct resource **and** the correct raw representation, but violate
> a required target state transition or command sequence.

For example:

```text
semantic intent: SetSetpoint(25 °C)

correct:
    enter-config
    write 250 -> 0x20
    observe ACK
    exit-config

mutated:
    write 250 -> 0x20
```

GREEN-2 should accept both if it has no protocol-state semantics.

That would justify the next layer rather than assuming it in advance.

## Kill condition retained

If representation correctness requires raw target values to appear in the
target-neutral semantic value itself, the abstraction boundary has failed.

GREEN-2 avoids that: raw `250` is derived by the target-specific
representation model.
