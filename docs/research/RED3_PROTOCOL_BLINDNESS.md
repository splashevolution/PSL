# RED-3 — Protocol-Blind Realization Check

**Branch:** `research/semantic-continuity-red3`  
**Baseline:** `3b36d61b0d5637ae52f2cd0c646e98f9d28c7054`

## Research question

After GREEN-2, can PSL distinguish two executions that use:

- the same correct semantic binding;
- the same correct raw representation;
- but different protocol/state sequences?

At this baseline, the answer is **no**.

## What RED-3 freezes

RED-1 changed the resource.

RED-2 changed the payload.

RED-3 changes neither.

Both executions use the exact same GREEN-2-correct write:

```text
resource = 0x20
raw      = 250
```

The only mutation is the surrounding protocol trace.

Reference trace:

```text
enter-config
issue-write
observe-ACK
exit-config
```

Mutated trace:

```text
issue-write
observe-ACK
```

## Machine-checked negative result

`lean/PSL/SemanticContinuityRed3.lean` introduces:

```text
CandidateExecution(Resource)
  write
  trace
```

and proves:

```text
reference.write = mutated.write
reference.trace != mutated.trace

GREEN2(reference) = true
GREEN2(mutated)   = true
```

This establishes the next narrow gap:

> **Binding correctness plus representation correctness is not protocol/state correctness.**

## Important claim boundary

RED-3 does **not** yet prove that the reference trace is valid or required, nor
that the mutated trace is invalid.

The current theory cannot express that relationship.

Those names describe the experiment setup relative to the planned stateful
device witness. GREEN-3 must introduce enough protocol semantics to make trace
validity a formal statement rather than a convention.

## Why GREEN-2 accepts both

GREEN-2 checks only:

```text
semantic identity
  -> target resource

semantic value
  -> raw representation
```

Both executions are identical along those dimensions.

GREEN-2 has no object for:

```text
initial state
  -> command
  -> next state
  -> observation
  -> ...
```

so the trace difference is invisible.

## GREEN-3 obligation

GREEN-3 should add the **minimum** state/transition semantics required to
distinguish the two traces.

The acceptance target is:

```text
same resource 0x20
same raw value 250

reference trace -> ACCEPT
mutated trace   -> REJECT
```

without:

- hard-coding one whole trace as a magic accepted list;
- trusting the realization generator;
- moving target protocol mechanics into the target-neutral semantic contract;
- adding persistence or timing before they are required;
- introducing QEMU/Renode yet.

A likely next object is a small target-specific protocol transition model, but
RED-3 intentionally does not prescribe the final architecture.

## Kill condition

If protocol correctness can only be established by embedding the entire target
command sequence into the target-neutral semantic contract, the continuity
boundary has failed.

The target-neutral intent must remain stable while target protocol machinery
remains replaceable.
