# RED-4 — Observation-Blind Realization Check

**Branch:** `research/semantic-continuity-red4`  
**Baseline:** `fdba805e5d58113622851c52f68e96735d83c5d1`

## Research question

After GREEN-3, can PSL distinguish two outcomes that contain the **same valid
modeled execution** but differ in whether the intended effect was observed?

At this baseline, the answer is **no**.

## What RED-4 freezes

RED-1 changed the resource.

RED-2 changed the representation.

RED-3 changed the protocol trace.

RED-4 changes none of those.

Both outcomes contain the exact same GREEN-3-valid execution:

```text
resource       = 0x20
raw write      = 250
protocol trace = enter-config
                 issue-write
                 observe-ACK
                 exit-config
```

The only mutation is the post-execution observation:

```text
reference observation = some 250
mutated observation   = none
```

## Machine-checked negative result

`lean/PSL/SemanticContinuityRed4.lean` introduces:

```text
CandidateOutcome(Resource, RawObservation)
  execution
  observation
```

and proves:

```text
reference.execution = mutated.execution
reference.observation != mutated.observation

GREEN3(reference) = true
GREEN3(mutated)   = true
```

This establishes the next narrow gap:

> **A valid modeled realization is not the same thing as an observed semantic effect.**

## Important claim boundary

RED-4 does **not** yet prove that raw observation `250` demonstrates the
intended semantic effect.

At this stage `some 250` is only the reference fixture for the next
falsification step.

The current theory has no independent relation connecting:

```text
semantic intent
    ->
executed realization
    ->
observable target state
```

That missing relation is the RED-4 result.

## Why GREEN-3 accepts both

GREEN-3 checks:

```text
semantic identity
    -> target resource

semantic value
    -> target representation

target trace
    -> protocol transition model
```

The two RED-4 outcomes are identical on all three dimensions.

GREEN-3 never inspects the post-execution observation, so absence of an
observation is invisible to it.

## GREEN-4 obligation

GREEN-4 should add the **minimum** observation/effect semantics required to
distinguish the outcomes.

The acceptance target is:

```text
same binding
same representation
same valid protocol trace

reference observed effect -> ACCEPT
missing observed effect   -> REJECT
```

without:

- trusting a realization-generated success flag;
- treating ACK alone as proof of semantic effect;
- embedding PVM32 observation details into the target-neutral semantic intent;
- claiming simulator or physical-device conformance prematurely.

A likely next object is an independent target-specific observation model that
relates concrete observable state back to the semantic value.

## Still-open boundary

GREEN-3's abstract `issueWrite` protocol marker is not yet parameterized by
the concrete payload. Resource/representation correctness and protocol
correctness are checked separately.

RED-4 does not silently solve that issue. It remains an explicit future attack
surface alongside observation provenance, persistence, timing, and target
conformance.

## Kill condition

If proof of semantic effect requires target-specific observations to be copied
into the target-neutral contract, the continuity boundary has failed.

The semantic contract should state the intended effect; target-specific
observation semantics should justify that effect independently.
