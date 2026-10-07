# PSL Semantic Architecture

## Status

This document describes the relationship between the **current implemented baseline** and the new **semantic-continuity research direction**.

The repository currently contains a verified PVM32/control-semantic line and an initial semantic-script / driver experiment. Those artifacts remain valid within their stated proof boundaries.

They are not the final definition of PSL.

## Current implemented separation

The present code establishes an initial separation:

```text
surface witness
      ↓
SemanticScript
      ↓
capability gate
      ↓
PVM32 binding / realization
```

`SemanticId` is deliberately distinct from a target address.

The PVM32 driver owns the binding from semantic identity to its target-specific byte/address representation.

This remains useful.

## Current limitation

The present `DriverContract` primarily asks whether a target **declares support** for required capabilities.

Conceptually:

```text
supports(write) = true
```

That does not establish realization correctness.

It cannot by itself prove that:

- the semantic identity is bound to the correct physical resource;
- the target representation uses the correct unit or scale;
- required device state transitions occur;
- acknowledgements/failures are handled correctly;
- persistence or atomicity requirements are satisfied.

Therefore capability acceptance is only an early gate.

## New target architecture

The research direction is:

```text
                     SemanticContract
                           │
                    observable meaning
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              realization A  realization B
                + evidence      + evidence
                    │             │
                    ▼             ▼
                  checker       checker
                    │             │
                DeviceModel A DeviceModel B
```

The realization generator may be untrusted.

The checker should fail closed when evidence does not establish that the target behavior satisfies the semantic contract.

## Semantic identity

The invariant survives from the earlier work:

> **Meaning is not a word. Meaning is not a hardware address.**

For the new research programme the stronger concern is:

> **A target binding is not correct merely because it is well-formed or capability-compatible. It must realize the required observable semantics.**

## PVM32 role

PVM32 remains **Driver / Realization 0**: a historical executable instance beneath the emerging theory.

It should eventually become one test case for the stronger realization relation rather than the definition of the semantic architecture.

## Surface-language experiment

The current kernel contains an explicit English/Devanagari witness.

That theorem is intentionally narrow: both surfaces are explicitly assigned the same `SemanticScript`. It is not evidence of independent multilingual elaboration and is no longer a central research line.

The witness may remain as historical implementation evidence until a later cleanup removes it safely.

## Evidence boundary

The intended long-term chain is:

```text
SemanticContract
      ↓ formal obligation
Realization + evidence
      ↓ checked relation
DeviceModel
      ↓ simulation / separate conformance evidence
Virtual or physical implementation
```

Each arrow must state its evidence class.

## Non-goals

This architecture does not currently claim:

- universal source-to-hardware correctness;
- equivalence between virtual hardware and physical silicon;
- that boolean capabilities constitute refinement proofs;
- that a specific source language is privileged;
- that Pāṇinian structures are necessary;
- that the continuity hypothesis is already established.

## Architectural invariant

Future PSL work should preserve:

> Semantic meaning is explicit.  
> Target realizations are independently justified.  
> Incompatible targets fail closed.  
> Proof boundaries remain visible.
