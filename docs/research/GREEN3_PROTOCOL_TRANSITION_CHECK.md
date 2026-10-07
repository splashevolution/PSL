# GREEN-3 — Target-Specific Protocol Transition Check

**Branch:** `research/semantic-continuity-green3`  
**Baseline:** `beef97449d50f10aea97d7556450501f5d377d3e`

## Result

GREEN-3 closes the exact protocol/state gap demonstrated by RED-3.

RED-3 established that two executions can share:

```text
resource = 0x20
raw      = 250
```

while differing only in protocol trace, and GREEN-2 still accepts both.

GREEN-3 adds one missing formal object:

```text
ProtocolModel(State, Step)
    initial
    transition
    accepting
```

plus an executable checker:

```text
checkProtocol(model, trace)
```

## Why this is not a magic accepted list

The PVM32 witness does not compare a trace to one hard-coded sequence.

It defines target-specific transitions:

```text
operational --enter-config--> config
config      --issue-write--> awaiting-ACK
awaiting-ACK --observe-ACK--> config
config      --exit-config--> operational
```

All other transitions fail closed.

Acceptance is determined by executing the trace through that state machine and
ending in an accepting state.

## Machine-checked result

`lean/PSL/SemanticContinuityGreen3.lean` proves:

```text
GREEN2(reference) = true
GREEN2(mutated)   = true

Protocol(reference) = true
Protocol(mutated)   = false

GREEN3(reference) = true
GREEN3(mutated)   = false
```

The generic theorem is:

```text
checkProtocol(model, trace) = true
    <->
protocolAccepts(model, trace)
```

So the executable checker is sound and complete for the transition relation
GREEN-3 actually states.

## Separation of concerns

The current target boundary now has three independent obligations:

```text
semantic identity
    -> DeviceModel
    -> target resource

semantic value
    -> RepresentationModel
    -> raw payload

target execution
    -> ProtocolModel
    -> valid state transitions
```

The target-neutral semantic quantity still contains no PVM32 address, fixed
point scale, or protocol state.

## Claim boundary

GREEN-3 proves protocol-sequence correctness **relative to the stated protocol
model**.

It does not yet prove that:

- an ACK was emitted by a real or simulated device;
- the written value persisted;
- timing constraints were met;
- an external observation confirms the semantic effect;
- the protocol model matches firmware or physical hardware.

Also, the RED-3 `ProtocolStep.issueWrite` marker is still abstract. GREEN-3
checks the candidate write separately through GREEN-2 and checks the protocol
trace separately; it does not yet prove that a concrete trace event carries
that exact payload.

That is a real remaining boundary, not hidden by this milestone.

## Why this remains minimal

RED-3 required only state-transition semantics.

GREEN-3 therefore does not yet introduce:

- physical or simulator I/O;
- wall-clock timing;
- persistence models;
- trace certificates;
- QEMU or Renode;
- hardware conformance claims.

Those should be justified by later counterexamples, not added pre-emptively.

## Next falsification direction

The next useful RED should attack the boundary between a valid modeled trace
and an actual observable effect.

One candidate is:

```text
valid protocol trace
correct resource
correct representation
ACK marker present

but no modeled observation that the intended device state changed
```

That would test whether PSL now needs an explicit observation/effect relation
rather than another static checker.

## Kill condition retained

If protocol correctness requires the target-specific transition sequence to be
embedded in the target-neutral semantic contract, the continuity boundary has
failed.

GREEN-3 avoids that: protocol machinery remains target-specific.
