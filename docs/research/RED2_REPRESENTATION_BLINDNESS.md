# RED-2 — Representation-Blind Binding Check

**Branch:** `research/semantic-continuity-red2`  
**Baseline:** `ebb21af2489e3a05a2fb17f6bb67657f7bba813e`

## Research question

After GREEN-1, can PSL distinguish two realizations that use the **same correct
resource binding** but carry **different raw representations**?

At this baseline, the answer is **no**.

## Why RED-2 is different from RED-1

RED-1 changed the physical resource:

```text
reference:   SemanticId(1001) -> 0x20
adversarial: SemanticId(1001) -> 0x21
```

GREEN-1 fixed that gap by independently modeling what each target resource
denotes.

RED-2 holds the resource fixed:

```text
resource: 0x20
```

and mutates only the target payload:

```text
reference raw value: 250
mutated raw value:    25
```

The intended motivating interpretation is a 25.0 °C setpoint on a legacy
fixed-point target, but RED-2 does not yet formalize that interpretation.

## Machine-checked negative result

`lean/PSL/SemanticContinuityRed2.lean` introduces a minimal:

```text
CandidateWrite(Resource)
  resource
  rawValue
```

and proves:

```text
reference.resource = mutated.resource
reference.rawValue != mutated.rawValue

GREEN1(reference) = true
GREEN1(mutated)   = true
```

This is enough to establish the next gap:

> **Binding correctness is not representation correctness.**

## Important claim boundary

RED-2 does **not** prove that raw value `250` is semantically correct or that
`25` is semantically wrong.

The current theory cannot express that relationship.

The words "reference" and "wrong-scale" describe the experiment setup relative
to the planned 25.0 °C witness. GREEN-2 must introduce enough representation
semantics to turn that convention into a formal statement.

## What GREEN-1 can see

GREEN-1 checks:

```text
semantic identity
      |
      v
target resource
      |
      v
device-model denotation
```

For both RED-2 candidates:

```text
SemanticId(1001)
      |
      v
0x20
      |
      v
SemanticId(1001)
```

So both correctly pass.

## What GREEN-1 cannot see

It has no relation for:

```text
semantic value
      |
      v
target representation
      |
      v
raw payload
```

Therefore changing only the payload is invisible to the checker.

## GREEN-2 obligation

GREEN-2 should add the **minimum** semantics required to state and check a
representation relation.

The acceptance target is:

```text
same resource 0x20

reference representation -> ACCEPT
mutated representation   -> REJECT
```

without:

- hard-coding raw value `250` into a supposedly target-neutral contract;
- trusting the realization generator;
- conflating resource binding with representation;
- adding protocol-state machinery before it is required;
- introducing QEMU/Renode yet.

A likely next object is a target-specific representation model or encoder
relation, but RED-2 intentionally does not prescribe its final shape.

## Kill condition

If representation correctness can only be obtained by embedding the target's
raw encoding directly in the semantic contract, then the abstraction boundary
has failed and should be redesigned.
