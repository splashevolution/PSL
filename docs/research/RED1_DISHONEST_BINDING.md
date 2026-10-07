# RED-1 — Binding-Blind Realization Gate

**Branch:** `research/semantic-continuity-red1`  
**Baseline:** `7317e0a6a1bb8c888dd52f1feed2c23074b4938e`

## Research question

Can the current PSL realization boundary distinguish a target that merely
provides a usable binding from a target binding that is semantically justified?

The answer at this baseline is **no**.

This is the first controlled RED result for the semantic-continuity research
line.

## Existing mechanism

The current PVM32 path has two independent pieces:

```text
DriverContract.supports
        │
        ▼
required capability gate

PVM32Bindings.targetOf
        │
        ▼
target-specific lowering
```

For `statusScript`, the reference mapping is:

```text
SemanticId(1001) -> 0x20
```

Nothing in the current formal model states why `0x20` is the semantically
correct resource.

## Adversarial witness

RED-1 introduces a second binding:

```text
SemanticId(1001) -> 0x21
```

The two mappings are different.

Yet both:

1. satisfy the same capability declaration;
2. provide a target for lowering;
3. produce a valid PVM32 word stream.

The resulting words differ:

```text
reference:   0x200520F0
adversarial: 0x200521F0
```

The current architecture has no formal object that can say which target
behavior actually realizes the semantic identity.

## Machine-checked negative result

`lean/PSL/SemanticContinuityRed1.lean` proves:

```text
reference binding ≠ adversarial binding

currentRealizationGate(reference, statusScript)   = true
currentRealizationGate(adversarial, statusScript) = true

lower(reference, statusScript) ≠
lower(adversarial, statusScript)
```

This keeps ordinary CI green while proving a negative fact about the current
design.

RED here means **the desired research property is false of the current
architecture**, not that the repository intentionally fails to build.

## Claim boundary

This experiment deliberately does **not** prove that physical address
`0x20` is correct and `0x21` is wrong.

That distinction cannot yet be represented.

Calling `0x21` adversarial is relative to the repository's existing
reference binding. GREEN-1 must introduce enough target semantics to make
correctness a formal statement rather than a convention.

## Why this matters

A boolean declaration such as:

```text
supports(write) = true
```

can establish only that an operation class is declared available.

It cannot establish:

```text
semantic identity
      ↓
correct target resource
      ↓
correct target behavior
```

Therefore:

> **Capability declaration is not realization correctness.**

That statement is now backed by a checked counterexample in the repository.

## GREEN-1 obligation

GREEN-1 should introduce the **minimum** theory needed to make the reference
and adversarial cases distinguishable.

Candidate objects are:

```text
DeviceModel
Realization
RealizationEvidence
RealizationChecker
Observation
```

But GREEN-1 should not add all of them merely because they appear in the
research charter. We should add only what the proof requires.

The acceptance target is:

```text
reference realization   -> ACCEPT
adversarial realization -> REJECT
```

without:

- placing target address `0x20` inside the target-neutral semantic contract;
- trusting the realization generator;
- modifying the historical PVM32 semantics to make the test pass;
- introducing QEMU/Renode yet;
- making a claim about physical hardware.

## Kill condition

If rejecting the adversarial binding requires hard-coding the expected
physical address into the semantic contract, then the proposed continuity
boundary has failed its first abstraction test.
